"""Orchestrate Portfolio Engine preflight, snapshots, persistence and recovery."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.portfolio import PortfolioItem, PortfolioRun
from nexora_api.schemas.portfolio import (
    OperationalValueInput,
    PortfolioOperationalInputs,
    PortfolioRequest,
)
from nexora_api.services.portfolio.metrics import (
    forecast_metrics,
    inventory_coverage,
    projected_exposure,
)
from nexora_api.services.portfolio.ranking import rank_items
from nexora_api.services.portfolio.risk import (
    CALCULATION_VERSION,
    COMPONENT_WEIGHTS,
    RISK_ORDER,
    classify_risk,
    priority_score,
    resolve_operational_inputs,
)
from nexora_api.services.portfolio.snapshot import freeze_forecast, select_forecast_runs, series_key

DEMO_RUN_ID = str(uuid5(NAMESPACE_URL, "nexora/portfolio/demo/v1"))
OPERATIONAL_FIELDS = [
    "current_inventory",
    "inbound_inventory",
    "safety_stock",
    "lead_time",
    "unit_cost",
    "service_level",
    "moq",
    "capacity",
]


def definitions() -> dict[str, object]:
    return {
        "calculation_version": CALCULATION_VERSION,
        "priority_formula": {
            "components": COMPONENT_WEIGHTS,
            "formula": "100 * sum(component * weight) / sum(valid weights)",
            "missing_rule": "renormalize_valid_components_without_rewarding_missing_data",
        },
        "risk_order": list(RISK_ORDER),
        "operational_fields": OPERATIONAL_FIELDS,
        "boundaries": [
            "forecast_is_not_inventory_decision",
            "no_automatic_execution",
            "no_inventory_optimization",
            "missing_is_not_zero",
            "priority_score_is_not_probability",
        ],
    }


def _candidate(run) -> dict[str, object]:
    return {
        "forecast_run_id": run.id,
        "dataset_id": run.dataset_id,
        "dataset_name": run.dataset.original_filename,
        "product": run.product,
        "location": run.location,
        "category": run.category,
        "frequency": run.frequency,
        "horizon": run.requested_horizon,
        "champion": str(run.champion_model),
        "created_at": run.created_at,
        "data_cutoff": run.data_cutoff.date().isoformat(),
    }


def portfolio_preflight(db: Session, payload: PortfolioRequest) -> dict[str, object]:
    runs = select_forecast_runs(
        db,
        dataset_id=payload.dataset_id,
        forecast_run_ids=payload.forecast_run_ids,
        cutoff=payload.cutoff,
        filters=payload.filters,
    )
    inputs_available = 0
    missing: list[str] = []
    for run in runs:
        inputs = payload.operational_inputs.get(run.id, PortfolioOperationalInputs())
        _, values, missing_fields, _, _ = resolve_operational_inputs(inputs, payload.cutoff)
        inputs_available += sum(value is not None for value in values.values())
        missing.extend(f"{run.id}:{field}" for field in missing_fields)
    warnings = ["operational_inputs_are_descriptive_not_executable"]
    if missing:
        warnings.append("portfolio_contains_missing_operational_inputs")
    return {
        "dataset_id": runs[0].dataset_id,
        "cutoff": payload.cutoff,
        "forecast_runs_found": len(runs),
        "series_compatible": len(runs),
        "frequency": runs[0].frequency,
        "horizon": runs[0].requested_horizon,
        "candidates": [_candidate(run) for run in runs],
        "operational_inputs_available": inputs_available,
        "missing_operational_inputs": missing,
        "valid_aggregations": ["same_dataset_same_frequency_same_horizon"],
        "invalid_aggregations": [],
        "warnings": warnings,
        "readiness": "warning" if missing else "ready",
    }


def _draft_item(
    *,
    item_id: str,
    key: str,
    product: str | None,
    location: str | None,
    category: str | None,
    family: str | None,
    forecast_run_id: str | None,
    champion: str,
    frequency: str,
    horizon: int,
    points: list[dict[str, object]],
    operational_inputs: PortfolioOperationalInputs,
    cutoff: datetime,
    provenance: dict[str, object],
) -> dict[str, object]:
    metrics = forecast_metrics(points)
    input_snapshot, values, missing, warnings, completeness = resolve_operational_inputs(
        operational_inputs, cutoff
    )
    coverage, coverage_status = inventory_coverage(
        values["current_inventory"], float(metrics["forecast_average"])
    )
    exposure = projected_exposure(
        float(metrics["forecast_total"]),
        values["current_inventory"],
        values["inbound_inventory"],
    )
    risk, reasons = classify_risk(
        coverage=coverage,
        horizon=horizon,
        current_inventory=values["current_inventory"],
        safety_stock=values["safety_stock"],
        lead_time=values["lead_time"],
    )
    if completeness != "sufficient_data":
        reasons.append("operational_data_incomplete")
    return {
        "id": item_id,
        "series_key": key,
        "product": product,
        "location": location,
        "category": category,
        "family": family,
        "forecast_run_id": forecast_run_id,
        "champion": champion,
        "forecast_horizon": horizon,
        "forecast_frequency": frequency,
        **metrics,
        "operational_inputs": input_snapshot,
        "current_inventory": values["current_inventory"],
        "inbound_inventory": values["inbound_inventory"],
        "safety_stock": values["safety_stock"],
        "lead_time": values["lead_time"],
        "inventory_coverage": coverage,
        "coverage_status": coverage_status,
        "projected_exposure": exposure,
        "operational_data_completeness": completeness,
        "risk_level": risk,
        "priority_reasons": reasons,
        "missing_inputs": missing,
        "warnings": warnings,
        "provenance": provenance,
    }


def _score_and_rank(items: list[dict[str, object]]) -> list[dict[str, object]]:
    maximum = max((float(item["forecast_total"]) for item in items), default=0.0)
    for item in items:
        score, status, components = priority_score(
            metrics=item,
            max_forecast_total=maximum,
            coverage=item["inventory_coverage"],
            horizon=int(item["forecast_horizon"]),
            current_inventory=item["current_inventory"],
            safety_stock=item["safety_stock"],
            lead_time=item["lead_time"],
        )
        item["priority_score"] = score
        item["score_status"] = status
        item["score_components"] = components
    return rank_items(items)


def _summary(items: list[dict[str, object]], *, aggregate_valid: bool) -> dict[str, object]:
    risk_counts = {level: 0 for level in RISK_ORDER}
    completeness_counts = {
        "sufficient_data": 0,
        "partial_data": 0,
        "insufficient_data": 0,
    }
    for item in items:
        risk_counts[str(item["risk_level"])] += 1
        completeness_counts[str(item["operational_data_completeness"])] += 1
    evaluable = sum(item["inventory_coverage"] is not None for item in items)
    return {
        "series_evaluated": len(items),
        "risk_counts": risk_counts,
        "completeness_counts": completeness_counts,
        "operational_information_coverage": evaluable / len(items) if items else 0.0,
        "forecast_aggregate_valid": aggregate_valid,
        "forecast_total_aggregate": sum(float(item["forecast_total"]) for item in items)
        if aggregate_valid
        else None,
        "forecast_peak_relevant": max(
            (float(item["forecast_peak"]) for item in items), default=None
        ),
        "coverage_evaluable_series": evaluable,
    }


def _persist_item(run: PortfolioRun, data: dict[str, object]) -> None:
    run.items.append(
        PortfolioItem(
            id=str(data["id"]),
            rank=int(data["rank"]),
            series_key=str(data["series_key"]),
            product=data["product"],
            location=data["location"],
            category=data["category"],
            family=data["family"],
            forecast_run_id=data["forecast_run_id"],
            champion=str(data["champion"]),
            forecast_horizon=int(data["forecast_horizon"]),
            forecast_frequency=str(data["forecast_frequency"]),
            forecast_total=float(data["forecast_total"]),
            forecast_average=float(data["forecast_average"]),
            forecast_peak=float(data["forecast_peak"]),
            forecast_minimum=float(data["forecast_minimum"]),
            forecast_variability=data["forecast_variability"],
            interval_json=data["interval_information"],
            operational_inputs_json=data["operational_inputs"],
            current_inventory=data["current_inventory"],
            inbound_inventory=data["inbound_inventory"],
            safety_stock=data["safety_stock"],
            lead_time=data["lead_time"],
            inventory_coverage=data["inventory_coverage"],
            coverage_status=str(data["coverage_status"]),
            projected_exposure=data["projected_exposure"],
            operational_data_completeness=str(data["operational_data_completeness"]),
            risk_level=str(data["risk_level"]),
            priority_score=float(data["priority_score"]),
            score_status=str(data["score_status"]),
            score_components=data["score_components"],
            priority_reasons=data["priority_reasons"],
            missing_inputs=data["missing_inputs"],
            warnings=data["warnings"],
            provenance_json=data["provenance"],
        )
    )


def create_portfolio(db: Session, payload: PortfolioRequest) -> PortfolioRun:
    preflight = portfolio_preflight(db, payload)
    runs = select_forecast_runs(
        db,
        dataset_id=payload.dataset_id,
        forecast_run_ids=payload.forecast_run_ids,
        cutoff=payload.cutoff,
        filters=payload.filters,
    )
    drafts: list[dict[str, object]] = []
    snapshots: list[dict[str, object]] = []
    for run in runs:
        snapshot = freeze_forecast(run)
        snapshots.append(snapshot)
        drafts.append(
            _draft_item(
                item_id=str(uuid4()),
                key=series_key(run),
                product=run.product,
                location=run.location,
                category=run.category,
                family=run.category,
                forecast_run_id=run.id,
                champion=str(run.champion_model),
                frequency=run.frequency,
                horizon=run.requested_horizon,
                points=list(snapshot["points"]),
                operational_inputs=payload.operational_inputs.get(
                    run.id, PortfolioOperationalInputs()
                ),
                cutoff=payload.cutoff,
                provenance={
                    "source": "persisted_forecast_run",
                    "forecast_snapshot": snapshot,
                    "official_forecast_modified": False,
                    "operational_inputs_declared_at_cutoff": True,
                },
            )
        )
    ranked = _score_and_rank(drafts)
    now = datetime.now(UTC)
    portfolio = PortfolioRun(
        id=str(uuid4()),
        dataset_id=str(preflight["dataset_id"]),
        source_mode="official",
        cutoff=payload.cutoff,
        created_at=now,
        available_at=now,
        calculation_version=CALCULATION_VERSION,
        forecast_run_ids=[run.id for run in runs],
        filters_json=payload.filters,
        number_of_series=len(ranked),
        summary_json=_summary(ranked, aggregate_valid=True),
        warnings=list(preflight["warnings"]),
        provenance_json={
            "selection_method": (
                "latest_completed_forecast_per_stable_series_key_available_at_cutoff"
            ),
            "forecast_snapshots": snapshots,
            "forecast_runs_modified": False,
            "aggregation_contract": "single_dataset_same_frequency_same_horizon",
        },
    )
    for item in ranked:
        _persist_item(portfolio, item)
    db.add(portfolio)
    db.commit()
    return require_portfolio(db, portfolio.id)


def _available(value: float, cutoff: datetime, reference: str) -> OperationalValueInput:
    return OperationalValueInput(
        value=value,
        status="available",
        available_at=cutoff,
        source_type="demo",
        source_reference=reference,
    )


def regenerate_demo(db: Session) -> PortfolioRun:
    existing = db.get(PortfolioRun, DEMO_RUN_ID)
    if existing is not None:
        db.delete(existing)
        db.flush()
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    specs = [
        ("NX-101", "Lima Centro", "Bebidas", [300, 320, 310, 340, 355, 360], (420, 90, 180, 2)),
        ("NX-204", "Arequipa", "Bebidas", [180, 185, 190, 195, 205, 210], (540, 120, 140, 2)),
        ("NX-330", "Lima Centro", "Cuidado", [95, 125, 90, 130, 100, 135], (420, None, None, None)),
        ("NX-455", "Cusco", "Cuidado", [70, 72, 71, 73, 72, 74], (None, None, None, None)),
        ("NX-501", "Trujillo", "Hogar", [110, 120, 115, 125, 118, 122], (360, 60, 100, 2)),
        ("NX-502", "Piura", "Hogar", [110, 120, 115, 125, 118, 122], (360, 60, 100, 2)),
    ]
    drafts: list[dict[str, object]] = []
    for product, location, category, values, inventory in specs:
        points = [
            {
                "timestamp": (cutoff + timedelta(weeks=index + 1)).date().isoformat(),
                "forecast": float(value),
                "lower_80": value * 0.9,
                "upper_80": value * 1.1,
                "lower_95": value * 0.8,
                "upper_95": value * 1.2,
            }
            for index, value in enumerate(values)
        ]
        current, inbound, safety, lead = inventory
        inputs = PortfolioOperationalInputs(
            current_inventory=_available(current, cutoff, "portfolio_demo_v1")
            if current is not None
            else OperationalValueInput(),
            inbound_inventory=_available(inbound, cutoff, "portfolio_demo_v1")
            if inbound is not None
            else OperationalValueInput(),
            safety_stock=_available(safety, cutoff, "portfolio_demo_v1")
            if safety is not None
            else OperationalValueInput(),
            lead_time=_available(lead, cutoff, "portfolio_demo_v1")
            if lead is not None
            else OperationalValueInput(),
        )
        drafts.append(
            _draft_item(
                item_id=str(uuid5(NAMESPACE_URL, f"nexora/portfolio/demo/v1/{product}/{location}")),
                key=f"demo|{product}|{location}|{category}|weekly",
                product=product,
                location=location,
                category=category,
                family=category,
                forecast_run_id=None,
                champion="demo_snapshot",
                frequency="weekly",
                horizon=len(values),
                points=points,
                operational_inputs=inputs,
                cutoff=cutoff,
                provenance={
                    "source": "synthetic_portfolio_demo",
                    "demo_version": "portfolio_demo_v1",
                    "does_not_create_forecast_runs": True,
                    "points": points,
                },
            )
        )
    ranked = _score_and_rank(drafts)
    now = datetime.now(UTC)
    portfolio = PortfolioRun(
        id=DEMO_RUN_ID,
        dataset_id=None,
        source_mode="demo",
        cutoff=cutoff,
        created_at=now,
        available_at=now,
        calculation_version=CALCULATION_VERSION,
        forecast_run_ids=[],
        filters_json={"demo": "portfolio_demo_v1"},
        number_of_series=len(ranked),
        summary_json=_summary(ranked, aggregate_valid=True),
        warnings=["demo_operational_data_not_company_data", "portfolio_is_not_inventory_decision"],
        provenance_json={
            "source": "deterministic_synthetic_portfolio_demo",
            "seed_contract": "fixed_specs_v1",
            "forecast_runs_created_or_modified": False,
        },
    )
    for item in ranked:
        _persist_item(portfolio, item)
    db.add(portfolio)
    db.commit()
    return require_portfolio(db, portfolio.id)


def _query(db: Session):
    return db.query(PortfolioRun).options(selectinload(PortfolioRun.items))


def require_portfolio(db: Session, portfolio_run_id: str) -> PortfolioRun:
    run = _query(db).filter(PortfolioRun.id == portfolio_run_id).one_or_none()
    if run is None:
        raise DataStudioError("portfolio_not_found", "El Portfolio Run solicitado no existe.", 404)
    return run


def serialize_item(item: PortfolioItem) -> dict[str, object]:
    return {
        "id": item.id,
        "rank": item.rank,
        "series_key": item.series_key,
        "product": item.product,
        "location": item.location,
        "category": item.category,
        "family": item.family,
        "forecast_run_id": item.forecast_run_id,
        "champion": item.champion,
        "forecast_horizon": item.forecast_horizon,
        "forecast_frequency": item.forecast_frequency,
        "forecast_total": item.forecast_total,
        "forecast_average": item.forecast_average,
        "forecast_peak": item.forecast_peak,
        "forecast_minimum": item.forecast_minimum,
        "forecast_variability": item.forecast_variability,
        "interval_information": item.interval_json,
        "operational_inputs": item.operational_inputs_json,
        "current_inventory": item.current_inventory,
        "inbound_inventory": item.inbound_inventory,
        "safety_stock": item.safety_stock,
        "lead_time": item.lead_time,
        "inventory_coverage": item.inventory_coverage,
        "coverage_status": item.coverage_status,
        "projected_exposure": item.projected_exposure,
        "operational_data_completeness": item.operational_data_completeness,
        "risk_level": item.risk_level,
        "priority_score": item.priority_score,
        "score_status": item.score_status,
        "score_components": item.score_components,
        "priority_reasons": item.priority_reasons,
        "missing_inputs": item.missing_inputs,
        "warnings": item.warnings,
        "provenance": item.provenance_json,
    }


def serialize_portfolio(run: PortfolioRun, *, include_items: bool = True) -> dict[str, object]:
    items = sorted(run.items, key=lambda item: (item.rank, item.series_key))
    return {
        "id": run.id,
        "dataset_id": run.dataset_id,
        "source_mode": run.source_mode,
        "cutoff": run.cutoff,
        "created_at": run.created_at,
        "available_at": run.available_at,
        "calculation_version": run.calculation_version,
        "forecast_run_ids": run.forecast_run_ids,
        "filters": run.filters_json,
        "number_of_series": run.number_of_series,
        "summary": run.summary_json,
        "warnings": run.warnings,
        "provenance": run.provenance_json,
        "items": [serialize_item(item) for item in items] if include_items else [],
    }


def list_portfolios(db: Session) -> list[dict[str, object]]:
    runs = (
        db.query(PortfolioRun)
        .order_by(PortfolioRun.created_at.desc(), PortfolioRun.id)
        .limit(100)
    )
    return [serialize_portfolio(run, include_items=False) for run in runs]
