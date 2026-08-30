"""Orchestrate scenario preflight, persistence, execution and recovery."""

from __future__ import annotations

from datetime import UTC, datetime, time
from uuid import uuid4

from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.context import ContextImpactEstimate, ContextSignal
from nexora_api.models.scenario import (
    ScenarioAssumption,
    ScenarioAudit,
    ScenarioPoint,
    ScenarioRun,
)
from nexora_api.schemas.scenario import ScenarioCreateRequest
from nexora_api.services.context.relevance import SeriesContext, match_signal
from nexora_api.services.forecasting.service import require_run as require_forecast_run
from nexora_api.services.scenarios.assumptions import context_provenance, validate_scope
from nexora_api.services.scenarios.baseline import date_text, prepare_baseline, verify_snapshot
from nexora_api.services.scenarios.combination import combine
from nexora_api.services.scenarios.comparison import summarize


def _selection(run) -> dict[str, object]:
    return {
        "dataset_id": run.dataset_id,
        "dataset_name": run.dataset.original_filename,
        "product": run.product,
        "location": run.location,
        "category": run.category,
        "frequency": run.frequency,
    }


def _eligible_context_impacts(db: Session, run) -> list[dict[str, object]]:
    cutoff = datetime.combine(run.data_cutoff.date(), time.max, UTC)
    estimates = (
        db.query(ContextImpactEstimate)
        .join(ContextSignal, ContextSignal.id == ContextImpactEstimate.signal_id)
        .filter(
            ContextImpactEstimate.dataset_id == run.dataset_id,
            ContextImpactEstimate.status == "estimated",
            ContextImpactEstimate.relative_delta.is_not(None),
            ContextImpactEstimate.data_cutoff <= cutoff,
            ContextSignal.available_at <= cutoff,
        )
        .order_by(ContextImpactEstimate.estimated_at.desc())
        .all()
    )
    context = SeriesContext(product=run.product, location=run.location, category=run.category)
    output: list[dict[str, object]] = []
    seen: set[str] = set()
    for estimate in estimates:
        if estimate.signal_id in seen:
            continue
        signal = db.get(ContextSignal, estimate.signal_id)
        if signal is None:
            continue
        matches, reasons = match_signal(signal, context)
        if not matches or signal.signal_type == "stockout":
            continue
        seen.add(signal.id)
        output.append(
            {
                "estimate_id": estimate.id,
                "signal_id": signal.id,
                "title": signal.title,
                "signal_type": signal.signal_type,
                "relative_delta": estimate.relative_delta,
                "evidence_score": estimate.evidence_score,
                "evidence_level": estimate.evidence_level,
                "event_periods": estimate.event_periods,
                "reference_periods": estimate.reference_periods,
                "baseline_value": estimate.baseline_value,
                "method": estimate.method,
                "match_reasons": reasons,
            }
        )
    return output


def preflight(db: Session, forecast_run_id: str) -> dict[str, object]:
    run = require_forecast_run(db, forecast_run_id)
    snapshot = prepare_baseline(run)
    return {
        "forecast_run_id": run.id,
        "dataset_id": run.dataset_id,
        "selection": _selection(run),
        "frequency": run.frequency,
        "horizon": run.requested_horizon,
        "champion_model": run.champion_model,
        "data_cutoff": date_text(run.data_cutoff),
        "baseline_points": list(snapshot["points"]),
        "eligible_context_impacts": _eligible_context_impacts(db, run),
        "warnings": [
            "scenario_does_not_modify_official_forecast",
            "conditional_result_not_future_guarantee",
        ],
    }


def create_scenario(db: Session, payload: ScenarioCreateRequest) -> ScenarioRun:
    forecast = require_forecast_run(db, payload.forecast_run_id)
    if payload.frequency is not None and payload.frequency != forecast.frequency:
        raise DataStudioError(
            "scenario_frequency_mismatch",
            "El escenario debe conservar la frecuencia del Forecast Run; "
            "no se inventa granularidad.",
            409,
        )
    snapshot = prepare_baseline(forecast)
    run = ScenarioRun(
        id=str(uuid4()),
        forecast_run_id=forecast.id,
        dataset_id=forecast.dataset_id,
        name=payload.name,
        description=payload.description,
        frequency=forecast.frequency,
        horizon=forecast.requested_horizon,
        champion_model=str(forecast.champion_model),
        data_cutoff=forecast.data_cutoff,
        selection_json=_selection(forecast),
        baseline_snapshot=snapshot,
        provenance_json={
            "baseline_contract": "persisted_forecast_run_points",
            "forecast_run_id": forecast.id,
            "champion_model": forecast.champion_model,
            "forecast_created_at": forecast.created_at.isoformat(),
            "baseline_sha256": snapshot["points_sha256"],
            "official_forecast_modified": False,
        },
        warnings=[
            "scenario_does_not_modify_official_forecast",
            "conditional_result_not_future_guarantee",
        ],
    )
    db.add(run)
    db.flush()
    for index, item in enumerate(payload.assumptions):
        validate_scope(item.scope, forecast)
        provenance, warnings = context_provenance(db, item, forecast)
        db.add(
            ScenarioAssumption(
                id=str(uuid4()),
                scenario_run_id=run.id,
                order_index=index,
                assumption_type=item.assumption_type,
                label=item.label,
                start_at=item.start_at,
                end_at=item.end_at,
                scope_json=item.scope,
                magnitude=item.magnitude,
                unit=item.unit,
                application_method=item.application_method,
                source_type=item.source_type,
                context_signal_id=item.context_signal_id,
                context_impact_estimate_id=item.context_impact_estimate_id,
                provenance_json=provenance,
                warnings=warnings,
            )
        )
    db.add(
        ScenarioAudit(
            scenario_run_id=run.id,
            action="created",
            details={
                "assumption_count": len(payload.assumptions),
                "baseline_sha256": snapshot["points_sha256"],
            },
        )
    )
    db.commit()
    return require_scenario(db, run.id)


def execute_scenario(db: Session, scenario_id: str) -> ScenarioRun:
    run = require_scenario(db, scenario_id)
    if run.status == "completed":
        return run
    baseline_points = verify_snapshot(run.baseline_snapshot)
    result_points, execution_warnings = combine(baseline_points, run.assumptions)
    run.points.clear()
    for item in result_points:
        run.points.append(
            ScenarioPoint(
                timestamp=datetime.combine(
                    datetime.fromisoformat(str(item["timestamp"])).date(), time.min, UTC
                ),
                baseline=float(item["baseline"]),
                scenario=float(item["scenario"]),
                absolute_delta=float(item["absolute_delta"]),
                relative_delta=item["relative_delta"],
                lower_80=item["lower_80"],
                upper_80=item["upper_80"],
                lower_95=item["lower_95"],
                upper_95=item["upper_95"],
                active_assumption_ids=list(item["active_assumption_ids"]),
            )
        )
    run.summary_json = summarize(result_points, len(run.assumptions))
    run.warnings = sorted(set(run.warnings) | set(execution_warnings))
    run.status = "completed"
    run.executed_at = datetime.now(UTC)
    db.add(
        ScenarioAudit(
            scenario_run_id=run.id,
            action="executed",
            details={
                "point_count": len(result_points),
                "warnings": execution_warnings,
                "combination": "declared_order",
                "baseline_sha256": run.baseline_snapshot["points_sha256"],
            },
        )
    )
    db.commit()
    return require_scenario(db, run.id)


def _query(db: Session):
    return db.query(ScenarioRun).options(
        selectinload(ScenarioRun.assumptions),
        selectinload(ScenarioRun.points),
        selectinload(ScenarioRun.audit_entries),
    )


def require_scenario(db: Session, scenario_id: str) -> ScenarioRun:
    run = _query(db).filter(ScenarioRun.id == scenario_id).one_or_none()
    if run is None:
        raise DataStudioError("scenario_not_found", "El escenario solicitado no existe.", 404)
    return run


def serialize_assumption(item: ScenarioAssumption) -> dict[str, object]:
    return {
        "id": item.id,
        "order_index": item.order_index,
        "assumption_type": item.assumption_type,
        "label": item.label,
        "start_at": item.start_at,
        "end_at": item.end_at,
        "scope": item.scope_json,
        "magnitude": item.magnitude,
        "unit": item.unit,
        "application_method": item.application_method,
        "source_type": item.source_type,
        "context_signal_id": item.context_signal_id,
        "context_impact_estimate_id": item.context_impact_estimate_id,
        "provenance": item.provenance_json,
        "warnings": item.warnings,
    }


def serialize_point(item: ScenarioPoint) -> dict[str, object]:
    return {
        "timestamp": date_text(item.timestamp),
        "baseline": item.baseline,
        "scenario": item.scenario,
        "absolute_delta": item.absolute_delta,
        "relative_delta": item.relative_delta,
        "lower_80": item.lower_80,
        "upper_80": item.upper_80,
        "lower_95": item.lower_95,
        "upper_95": item.upper_95,
        "active_assumption_ids": item.active_assumption_ids,
    }


def serialize_scenario(run: ScenarioRun, *, include_details: bool = True) -> dict[str, object]:
    assumptions = sorted(run.assumptions, key=lambda item: item.order_index)
    points = sorted(run.points, key=lambda item: item.timestamp)
    audits = sorted(run.audit_entries, key=lambda item: (item.created_at, item.id))
    return {
        "id": run.id,
        "forecast_run_id": run.forecast_run_id,
        "dataset_id": run.dataset_id,
        "name": run.name,
        "description": run.description,
        "status": run.status,
        "frequency": run.frequency,
        "horizon": run.horizon,
        "champion_model": run.champion_model,
        "data_cutoff": date_text(run.data_cutoff),
        "selection": run.selection_json,
        "baseline_snapshot": run.baseline_snapshot,
        "provenance": run.provenance_json,
        "summary": run.summary_json,
        "warnings": run.warnings,
        "created_at": run.created_at,
        "executed_at": run.executed_at,
        "total_relative_delta": run.summary_json.get("relative_delta"),
        "assumptions": [serialize_assumption(item) for item in assumptions]
        if include_details
        else [],
        "points": [serialize_point(item) for item in points] if include_details else [],
        "audit": [
            {
                "id": item.id,
                "action": item.action,
                "details": item.details,
                "created_at": item.created_at,
            }
            for item in audits
        ]
        if include_details
        else [],
    }


def list_scenarios(db: Session, forecast_run_id: str | None = None) -> list[dict[str, object]]:
    query = db.query(ScenarioRun)
    if forecast_run_id:
        query = query.filter(ScenarioRun.forecast_run_id == forecast_run_id)
    runs = query.order_by(ScenarioRun.created_at.desc()).limit(100).all()
    return [serialize_scenario(run, include_details=False) for run in runs]
