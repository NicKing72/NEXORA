"""Inventory Engine orchestration, persistence, demo and serialization."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4, uuid5

from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.inventory import InventoryItem, InventoryRun
from nexora_api.schemas.inventory import (
    InventoryOperationalInputs,
    InventoryRequest,
    InventoryValueInput,
)
from nexora_api.services.inventory.compatibility import resolve_sources
from nexora_api.services.inventory.coverage import coverage_views
from nexora_api.services.inventory.demand import demand_metrics, demand_points
from nexora_api.services.inventory.eoq import calculate_eoq
from nexora_api.services.inventory.reorder import (
    TIME_UNIT_BY_FREQUENCY,
    compatible_lead_time,
    demand_during_lead_time,
    reorder_point,
)
from nexora_api.services.inventory.replenishment import calculate_replenishment
from nexora_api.services.inventory.risk import classify_risk
from nexora_api.services.inventory.safety_stock import (
    Z_SCORES,
    calculate_safety_stock,
    interval_sigma,
)
from nexora_api.services.inventory.snapshot import freeze_sources, resolve_inputs

CALCULATION_VERSION = "inventory_replenishment_v1"
DEMO_RUN_ID = str(uuid5(UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"), "nexora-inventory-demo-v1"))


def definitions() -> dict[str, object]:
    return {
        "calculation_version": CALCULATION_VERSION,
        "formulas": {
            "coverage": "inventory / average forecast demand",
            "safety_stock": "z × sigma_period × sqrt(lead_time_periods)",
            "reorder_point": "lead_time_demand + safety_stock",
            "eoq": "sqrt((2 × annual_demand × order_cost) / annual_holding_cost)",
            "net_requirement": (
                "forecast + safety_stock + commitments + backorders - on_hand - eligible_transit"
            ),
        },
        "service_levels": {str(key): value for key, value in Z_SCORES.items()},
        "compatible_time_units": TIME_UNIT_BY_FREQUENCY,
        "risk_rules": [
            "critical: projected shortage or coverage below lead time",
            "high: coverage within 25% above lead time",
            "medium: projected surplus greater than forecast horizon demand",
            "low: no quantified shortage/excess signal",
            "unknown: insufficient inventory evidence",
        ],
        "boundaries": [
            "no purchase order execution",
            "no missing value becomes zero",
            "no Forecast Run mutation",
            "risk is descriptive, not a probability",
        ],
    }


def _calculation(
    formula: str,
    substitution: str | None,
    result: float | None,
    *,
    unit: str = "units",
    reason: str | None = None,
) -> dict[str, object]:
    return {
        "formula": formula,
        "substitution": substitution,
        "result": result,
        "unit": unit,
        "status": "calculated" if result is not None else "not_calculable",
        "reason": reason,
    }


def compute_item(
    *,
    points: list[dict[str, object]],
    frequency: str,
    product: str | None,
    location: str | None,
    category: str | None,
    forecast_run_id: str | None,
    demand_source: str,
    input_snapshot: dict[str, object],
    values: dict[str, float | None],
    missing_inputs: list[str],
    input_warnings: list[str],
    include_in_transit: bool,
) -> dict[str, object]:
    metrics = demand_metrics(points)
    demand_values = [float(point["demand"]) for point in points]
    on_hand, transit = values["inventory_on_hand"], values["inventory_in_transit"]
    physical_coverage, transit_coverage = coverage_views(on_hand, transit, metrics["average"])
    lead_item = input_snapshot["lead_time"]
    lead_unit = lead_item.get("unit") if isinstance(lead_item, dict) else None
    lead_periods = compatible_lead_time(
        frequency, values["lead_time"], str(lead_unit) if lead_unit else None
    )
    lt_demand = demand_during_lead_time(demand_values, lead_periods)
    sigma = interval_sigma(points)
    declared_ss = values["safety_stock"]
    if declared_ss is not None:
        safety_stock = declared_ss
        safety_source = "declared"
        ss_calc = _calculation("declared safety stock", f"{declared_ss:g}", declared_ss)
    else:
        safety_stock, ss_calc = calculate_safety_stock(
            service_level=values["service_level"],
            sigma_period=sigma,
            lead_time_periods=lead_periods,
        )
        safety_source = "calculated" if safety_stock is not None else None
    rop = reorder_point(lt_demand, safety_stock)
    eoq, eoq_calc, annual_holding = calculate_eoq(
        average_demand=metrics["average"],
        frequency=frequency,
        order_cost=values["order_cost"],
        holding_cost=values["holding_cost"],
        holding_rate=values["holding_rate"],
        unit_cost=values["unit_cost"],
    )
    eligible_transit = transit if include_in_transit else None
    replenishment = calculate_replenishment(
        forecast_total=metrics["total"],
        on_hand=on_hand,
        eligible_transit=eligible_transit,
        safety_stock=safety_stock,
        committed=values["committed_inventory"],
        backorders=values["backorders"],
        moq=values["moq"],
        lot_multiple=values["lot_multiple"],
        capacity=values["capacity"],
    )
    if lead_periods is None:
        replenishment["recommended_quantity"] = None
        replenishment["warnings"] = [
            *replenishment["warnings"],
            "manual_review_required_incompatible_or_missing_lead_time",
        ]
    risk, risk_reasons = classify_risk(
        physical_coverage=physical_coverage,
        lead_time_periods=lead_periods,
        shortage=replenishment["shortage"],
        surplus=replenishment["surplus"],
        forecast_total=metrics["total"],
    )
    risk_label = {
        "critical": "crítico",
        "high": "alto",
        "medium": "medio",
        "low": "bajo",
        "unknown": "desconocido",
    }[risk]
    risk_reason_labels = {
        "projected_shortage": "Se proyecta un faltante bajo los supuestos declarados.",
        "coverage_below_lead_time": "La cobertura física es inferior al lead time.",
        "coverage_near_lead_time": "La cobertura física está muy próxima al lead time.",
        "significant_projected_surplus": "El excedente supera la demanda del horizonte.",
        "no_quantified_shortage_or_excess_signal": "No se cuantificó faltante ni exceso relevante.",
        "insufficient_inventory_evidence": "No existe evidencia de inventario suficiente.",
    }
    applicable = [
        item
        for item in input_snapshot.values()
        if isinstance(item, dict) and item.get("status") != "not_applicable"
    ]
    available = [item for item in applicable if item.get("status") == "available"]
    completeness = round(100 * len(available) / len(applicable), 2) if applicable else 100.0
    warnings = list(dict.fromkeys([*input_warnings, *replenishment["warnings"]]))
    if lead_periods is None and values["lead_time"] is not None:
        warnings.append("lead_time_unit_incompatible_with_forecast_frequency")
    calculations = {
        "physical_coverage": _calculation(
            "on_hand / average_forecast_demand",
            f"{on_hand:g} / {metrics['average']:.6f}"
            if on_hand is not None and metrics["average"] > 0
            else None,
            physical_coverage,
            unit=TIME_UNIT_BY_FREQUENCY.get(frequency, "periods"),
            reason="missing_inventory_or_non_positive_demand"
            if physical_coverage is None
            else None,
        ),
        "coverage_with_transit": _calculation(
            "(on_hand + in_transit) / average_forecast_demand",
            f"({on_hand:g} + {transit:g}) / {metrics['average']:.6f}"
            if on_hand is not None and transit is not None and metrics["average"] > 0
            else None,
            transit_coverage,
            unit=TIME_UNIT_BY_FREQUENCY.get(frequency, "periods"),
            reason="requires_explicit_on_hand_and_transit" if transit_coverage is None else None,
        ),
        "lead_time_demand": _calculation(
            "sum forecast demand over compatible lead-time periods",
            f"first {lead_periods:g} {lead_unit}" if lead_periods is not None else None,
            lt_demand,
            reason="missing_incompatible_or_out_of_horizon_lead_time"
            if lt_demand is None
            else None,
        ),
        "safety_stock": ss_calc,
        "reorder_point": _calculation(
            "lead_time_demand + safety_stock",
            f"{lt_demand:.6f} + {safety_stock:.6f}"
            if lt_demand is not None and safety_stock is not None
            else None,
            rop,
            reason="lead_time_demand_or_safety_stock_missing" if rop is None else None,
        ),
        "eoq": eoq_calc,
        "net_requirement": _calculation(
            "forecast + safety_stock + committed + backorders - on_hand - eligible_transit",
            None,
            replenishment["raw_requirement"],
            reason="critical_operational_inputs_missing"
            if replenishment["raw_requirement"] is None
            else None,
        ),
    }
    return {
        "forecast_run_id": forecast_run_id,
        "product": product,
        "location": location,
        "category": category,
        "frequency": frequency,
        "horizon": len(points),
        "demand_source": demand_source,
        "forecast_total": metrics["total"],
        "forecast_average": metrics["average"],
        "inventory_on_hand": on_hand,
        "inventory_in_transit": transit,
        "safety_stock": safety_stock,
        "safety_stock_source": safety_source,
        "lead_time": values["lead_time"],
        "lead_time_unit": str(lead_unit) if lead_unit else None,
        "service_level": values["service_level"],
        "unit_cost": values["unit_cost"],
        "order_cost": values["order_cost"],
        "holding_cost": annual_holding,
        "moq": values["moq"],
        "capacity": values["capacity"],
        "physical_coverage": physical_coverage,
        "coverage_with_transit": transit_coverage,
        "lead_time_demand": lt_demand,
        "reorder_point": rop,
        "eoq": eoq,
        "projected_inventory": replenishment["projected_inventory"],
        "projected_shortage": replenishment["shortage"],
        "projected_surplus": replenishment["surplus"],
        "raw_requirement": replenishment["raw_requirement"],
        "recommended_quantity": replenishment["recommended_quantity"],
        "risk_level": risk,
        "completeness": completeness,
        "inputs": input_snapshot,
        "calculations": calculations,
        "constraints": replenishment["constraints"],
        "missing_inputs": missing_inputs,
        "warnings": warnings,
        "explanation": {
            "detected": f"Riesgo de inventario {risk_label} según la evidencia calculable.",
            "why_it_matters": " ".join(risk_reason_labels[reason] for reason in risk_reasons),
            "data_used": "Pronóstico persistido y entradas operativas declaradas.",
            "data_missing": missing_inputs,
            "review": (
                "Revisar cobertura, punto de reorden y restricciones antes de ejecutar una acción."
            ),
            "cannot_conclude": (
                "No garantiza ventas futuras ni ejecuta compras, transferencias "
                "o cambios de inventario."
            ),
        },
        "evidence": {
            "demand_points": points,
            "sigma_period": sigma,
            "eligible_in_transit": include_in_transit,
            "risk_reasons": risk_reasons,
        },
    }


def _persist_item(run: InventoryRun, draft: dict[str, object]) -> None:
    run.items.append(
        InventoryItem(
            id=str(uuid4()),
            inventory_run_id=run.id,
            forecast_run_id=draft["forecast_run_id"],
            product=draft["product"],
            location=draft["location"],
            category=draft["category"],
            frequency=draft["frequency"],
            horizon=draft["horizon"],
            demand_source=draft["demand_source"],
            forecast_total=draft["forecast_total"],
            forecast_average=draft["forecast_average"],
            inventory_on_hand=draft["inventory_on_hand"],
            inventory_in_transit=draft["inventory_in_transit"],
            safety_stock=draft["safety_stock"],
            safety_stock_source=draft["safety_stock_source"],
            lead_time=draft["lead_time"],
            lead_time_unit=draft["lead_time_unit"],
            service_level=draft["service_level"],
            unit_cost=draft["unit_cost"],
            order_cost=draft["order_cost"],
            holding_cost=draft["holding_cost"],
            moq=draft["moq"],
            capacity=draft["capacity"],
            physical_coverage=draft["physical_coverage"],
            coverage_with_transit=draft["coverage_with_transit"],
            lead_time_demand=draft["lead_time_demand"],
            reorder_point=draft["reorder_point"],
            eoq=draft["eoq"],
            projected_inventory=draft["projected_inventory"],
            projected_shortage=draft["projected_shortage"],
            projected_surplus=draft["projected_surplus"],
            raw_requirement=draft["raw_requirement"],
            recommended_quantity=draft["recommended_quantity"],
            risk_level=draft["risk_level"],
            completeness=draft["completeness"],
            inputs_json=draft["inputs"],
            calculations_json=draft["calculations"],
            constraints_json=draft["constraints"],
            missing_inputs=draft["missing_inputs"],
            warnings=draft["warnings"],
            explanation_json=draft["explanation"],
            evidence_json=draft["evidence"],
        )
    )


def _summary(items: list[dict[str, object]]) -> dict[str, object]:
    risks = {key: 0 for key in ("critical", "high", "medium", "low", "unknown")}
    for item in items:
        risks[str(item["risk_level"])] += 1
    shortages = [
        float(item["projected_shortage"])
        for item in items
        if item["projected_shortage"] is not None
    ]
    surpluses = [
        float(item["projected_surplus"]) for item in items if item["projected_surplus"] is not None
    ]
    return {
        "series_analyzed": len(items),
        "risk_counts": risks,
        "insufficient_coverage": sum(item["risk_level"] in {"critical", "high"} for item in items),
        "projected_shortage": sum(shortages) if shortages else None,
        "projected_surplus": sum(surpluses) if surpluses else None,
        "calculable_recommendations": sum(
            item["recommended_quantity"] is not None for item in items
        ),
        "manual_review_required": sum(item["recommended_quantity"] is None for item in items),
        "input_completeness": round(
            sum(float(item["completeness"]) for item in items) / len(items), 2
        )
        if items
        else 0,
    }


def inventory_preflight(db: Session, payload: InventoryRequest) -> dict[str, object]:
    forecast, scenario, portfolio, decision = resolve_sources(
        db,
        forecast_run_id=payload.forecast_run_id,
        scenario_run_id=payload.scenario_run_id,
        portfolio_run_id=payload.portfolio_run_id,
        decision_run_id=payload.decision_run_id,
        cutoff=payload.cutoff,
    )
    snapshot, values, missing, warnings = resolve_inputs(payload.operational_inputs, payload.cutoff)
    source, points = demand_points(forecast, scenario)
    lead_unit = snapshot["lead_time"].get("unit")
    lead_ok = compatible_lead_time(forecast.frequency, values["lead_time"], lead_unit) is not None
    declared_ss = values["safety_stock"] is not None
    calculated_ss = (
        values["service_level"] is not None and interval_sigma(points) is not None and lead_ok
    )
    calculable = {
        "coverage": values["inventory_on_hand"] is not None,
        "lead_time_demand": lead_ok,
        "safety_stock": declared_ss or calculated_ss,
        "reorder_point": lead_ok and (declared_ss or calculated_ss),
        "eoq": values["order_cost"] is not None
        and (
            values["holding_cost"] is not None
            or (values["holding_rate"] is not None and values["unit_cost"] is not None)
        ),
        "recommended_quantity": values["inventory_on_hand"] is not None
        and lead_ok
        and (declared_ss or calculated_ss),
    }
    return {
        "forecast_run_id": forecast.id,
        "dataset_id": forecast.dataset_id,
        "scenario_run_id": scenario.id if scenario else None,
        "portfolio_run_id": portfolio.id if portfolio else None,
        "decision_run_id": decision.id if decision else None,
        "cutoff": payload.cutoff,
        "product": forecast.product,
        "location": forecast.location,
        "category": forecast.category,
        "frequency": forecast.frequency,
        "horizon": forecast.requested_horizon,
        "champion": forecast.champion_model,
        "demand_source": source,
        "available_inputs": sorted(name for name, value in values.items() if value is not None),
        "missing_inputs": missing,
        "calculable": calculable,
        "readiness": "ready" if all(calculable.values()) else "warning",
        "warnings": warnings,
    }


def create_inventory(db: Session, payload: InventoryRequest) -> InventoryRun:
    forecast, scenario, portfolio, decision = resolve_sources(
        db,
        forecast_run_id=payload.forecast_run_id,
        scenario_run_id=payload.scenario_run_id,
        portfolio_run_id=payload.portfolio_run_id,
        decision_run_id=payload.decision_run_id,
        cutoff=payload.cutoff,
    )
    input_snapshot, values, missing, input_warnings = resolve_inputs(
        payload.operational_inputs, payload.cutoff
    )
    source, points = demand_points(forecast, scenario)
    draft = compute_item(
        points=points,
        frequency=forecast.frequency,
        product=forecast.product,
        location=forecast.location,
        category=forecast.category,
        forecast_run_id=forecast.id,
        demand_source=source,
        input_snapshot=input_snapshot,
        values=values,
        missing_inputs=missing,
        input_warnings=input_warnings,
        include_in_transit=payload.include_in_transit,
    )
    now = datetime.now(UTC)
    run = InventoryRun(
        id=str(uuid4()),
        dataset_id=forecast.dataset_id,
        forecast_run_id=forecast.id,
        scenario_run_id=scenario.id if scenario else None,
        portfolio_run_id=portfolio.id if portfolio else None,
        decision_run_id=decision.id if decision else None,
        source_mode="official",
        cutoff=payload.cutoff,
        created_at=now,
        available_at=now,
        calculation_version=CALCULATION_VERSION,
        status="completed",
        source_snapshot=freeze_sources(forecast, scenario, portfolio, decision, points),
        assumptions_json={
            "include_in_transit": payload.include_in_transit,
            "transit_is_not_assumed_immediately_available": True,
        },
        missing_inputs=missing,
        scope_json={
            "product": forecast.product,
            "location": forecast.location,
            "category": forecast.category,
            "frequency": forecast.frequency,
        },
        coverage_json={"input_completeness": draft["completeness"]},
        summary_json=_summary([draft]),
        warnings=draft["warnings"],
        provenance_json={
            "calculation_version": CALCULATION_VERSION,
            "forecast_modified": False,
            "scenario_modified": False,
            "executes_orders": False,
        },
    )
    _persist_item(run, draft)
    db.add(run)
    db.commit()
    return require_inventory(db, run.id)


def _demo_input(**values: tuple[float, str]) -> InventoryOperationalInputs:
    kwargs = {
        name: InventoryValueInput(
            value=value[0],
            status="available",
            unit=value[1],
            source_type="demo",
            source_reference="inventory_demo_v1",
        )
        for name, value in values.items()
    }
    return InventoryOperationalInputs(**kwargs)


def regenerate_demo(db: Session) -> InventoryRun:
    existing = db.get(InventoryRun, DEMO_RUN_ID)
    if existing:
        db.delete(existing)
        db.flush()
    specs = [
        (
            "NX-101",
            "Lima Centro",
            40,
            dict(
                inventory_on_hand=(80, "units"),
                inventory_in_transit=(40, "units"),
                lead_time=(5, "days"),
                service_level=(0.95, "ratio"),
                order_cost=(30, "currency/order"),
                holding_cost=(3, "currency/unit/year"),
                moq=(100, "units"),
                lot_multiple=(25, "units"),
            ),
        ),
        (
            "NX-205",
            "Lima Centro",
            18,
            dict(
                inventory_on_hand=(300, "units"), lead_time=(3, "days"), safety_stock=(45, "units")
            ),
        ),
        (
            "NX-310",
            "Arequipa",
            25,
            dict(
                inventory_on_hand=(20, "units"),
                lead_time=(7, "days"),
                safety_stock=(60, "units"),
                capacity=(250, "units"),
            ),
        ),
        (
            "NX-415",
            "Arequipa",
            12,
            dict(
                inventory_on_hand=(900, "units"), lead_time=(2, "days"), safety_stock=(30, "units")
            ),
        ),
        (
            "NX-520",
            "Lima Centro",
            30,
            dict(
                inventory_on_hand=(100, "units"),
                lead_time=(4, "days"),
                service_level=(0.99, "ratio"),
                unit_cost=(20, "currency/unit"),
                holding_rate=(0.2, "ratio/year"),
                order_cost=(50, "currency/order"),
            ),
        ),
        (
            "NX-625",
            "Arequipa",
            16,
            dict(
                inventory_on_hand=(120, "units"), lead_time=(3, "days"), safety_stock=(20, "units")
            ),
        ),
        (
            "NX-730",
            "Lima Centro",
            22,
            dict(
                inventory_on_hand=(60, "units"),
                inventory_in_transit=(180, "units"),
                lead_time=(6, "days"),
                safety_stock=(35, "units"),
                moq=(80, "units"),
            ),
        ),
        ("NX-835", "Arequipa", 20, dict()),
    ]
    drafts = []
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    for index, (product, location, base, inputs) in enumerate(specs):
        points = [
            {
                "timestamp": f"2026-01-{day:02d}T00:00:00+00:00",
                "demand": float(base + (day % 3) - 1),
                "lower_95": float(base - 5),
                "upper_95": float(base + 5),
            }
            for day in range(1, 15)
        ]
        input_snapshot, resolved, missing, warnings = resolve_inputs(_demo_input(**inputs), cutoff)
        drafts.append(
            compute_item(
                points=points,
                frequency="daily",
                product=product,
                location=location,
                category="Demo",
                forecast_run_id=None,
                demand_source="synthetic_demo",
                input_snapshot=input_snapshot,
                values=resolved,
                missing_inputs=missing,
                input_warnings=warnings,
                include_in_transit=index == 6,
            )
        )
    now = datetime.now(UTC)
    run = InventoryRun(
        id=DEMO_RUN_ID,
        dataset_id=None,
        forecast_run_id=None,
        source_mode="demo",
        cutoff=cutoff,
        created_at=now,
        available_at=now,
        calculation_version=CALCULATION_VERSION,
        status="completed",
        source_snapshot={
            "source": "deterministic_synthetic_inventory_demo",
            "forecast_runs_created_or_modified": False,
        },
        assumptions_json={"demo_version": "inventory_demo_v1"},
        missing_inputs=sorted({name for item in drafts for name in item["missing_inputs"]}),
        scope_json={"frequency": "daily", "series": len(drafts)},
        coverage_json={"input_completeness": _summary(drafts)["input_completeness"]},
        summary_json=_summary(drafts),
        warnings=["demo_data_not_company_inventory", "no_orders_are_executed"],
        provenance_json={
            "deterministic": True,
            "calculation_version": CALCULATION_VERSION,
            "forecast_modified": False,
            "executes_orders": False,
        },
    )
    for draft in drafts:
        _persist_item(run, draft)
    db.add(run)
    db.commit()
    return require_inventory(db, run.id)


def _query(db: Session):
    return db.query(InventoryRun).options(selectinload(InventoryRun.items))


def require_inventory(db: Session, run_id: str) -> InventoryRun:
    run = _query(db).filter(InventoryRun.id == run_id).one_or_none()
    if run is None:
        raise DataStudioError("inventory_run_not_found", "El Inventory Run no existe.", 404)
    return run


def serialize_item(item: InventoryItem) -> dict[str, object]:
    return {
        "id": item.id,
        "forecast_run_id": item.forecast_run_id,
        "product": item.product,
        "location": item.location,
        "category": item.category,
        "frequency": item.frequency,
        "horizon": item.horizon,
        "demand_source": item.demand_source,
        "forecast_total": item.forecast_total,
        "forecast_average": item.forecast_average,
        "inventory_on_hand": item.inventory_on_hand,
        "inventory_in_transit": item.inventory_in_transit,
        "safety_stock": item.safety_stock,
        "safety_stock_source": item.safety_stock_source,
        "lead_time": item.lead_time,
        "lead_time_unit": item.lead_time_unit,
        "service_level": item.service_level,
        "unit_cost": item.unit_cost,
        "order_cost": item.order_cost,
        "holding_cost": item.holding_cost,
        "moq": item.moq,
        "capacity": item.capacity,
        "physical_coverage": item.physical_coverage,
        "coverage_with_transit": item.coverage_with_transit,
        "lead_time_demand": item.lead_time_demand,
        "reorder_point": item.reorder_point,
        "eoq": item.eoq,
        "projected_inventory": item.projected_inventory,
        "projected_shortage": item.projected_shortage,
        "projected_surplus": item.projected_surplus,
        "raw_requirement": item.raw_requirement,
        "recommended_quantity": item.recommended_quantity,
        "risk_level": item.risk_level,
        "completeness": item.completeness,
        "inputs": item.inputs_json,
        "calculations": item.calculations_json,
        "constraints": item.constraints_json,
        "missing_inputs": item.missing_inputs,
        "warnings": item.warnings,
        "explanation": item.explanation_json,
        "evidence": item.evidence_json,
    }


def serialize_inventory(run: InventoryRun, *, include_items: bool = True) -> dict[str, object]:
    return {
        "id": run.id,
        "dataset_id": run.dataset_id,
        "forecast_run_id": run.forecast_run_id,
        "scenario_run_id": run.scenario_run_id,
        "portfolio_run_id": run.portfolio_run_id,
        "decision_run_id": run.decision_run_id,
        "source_mode": run.source_mode,
        "cutoff": run.cutoff,
        "created_at": run.created_at,
        "available_at": run.available_at,
        "calculation_version": run.calculation_version,
        "status": run.status,
        "source_snapshot": run.source_snapshot,
        "assumptions": run.assumptions_json,
        "missing_inputs": run.missing_inputs,
        "scope": run.scope_json,
        "coverage": run.coverage_json,
        "summary": run.summary_json,
        "warnings": run.warnings,
        "provenance": run.provenance_json,
        "items": [serialize_item(item) for item in run.items] if include_items else [],
    }


def list_inventory_runs(db: Session) -> list[dict[str, object]]:
    return [
        serialize_inventory(run, include_items=False)
        for run in db.query(InventoryRun)
        .order_by(InventoryRun.created_at.desc(), InventoryRun.id)
        .limit(100)
    ]
