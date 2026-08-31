"""Collect temporally safe immutable decision evidence."""

from __future__ import annotations

from datetime import UTC, datetime, time
from statistics import median

from sqlalchemy import or_
from sqlalchemy.orm import Session

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.context import ContextImpactEstimate, ContextSignal
from nexora_api.models.dataset import ForecastRun
from nexora_api.models.scenario import ScenarioRun
from nexora_api.services.context.impact.analogies import scopes_are_compatible
from nexora_api.services.context.relevance import SeriesContext, match_signal
from nexora_api.services.decisions.portfolio_evidence import (
    list_available_portfolios,
    prepare_portfolio_evidence,
)
from nexora_api.services.decisions.scor_evidence import (
    list_available_scor_assessments,
    prepare_scor_evidence,
)
from nexora_api.services.forecasting.service import require_run as require_forecast
from nexora_api.services.scenarios.service import require_scenario

MISSING_OPERATIONAL_INPUTS = [
    "current_inventory_position",
    "lead_time",
    "minimum_order_quantity",
    "holding_cost",
    "stockout_cost",
    "target_service_level",
]


def _utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _forecast_cutoff(run: ForecastRun) -> datetime:
    return datetime.combine(run.data_cutoff.date(), time.max, UTC)


def _selection(run: ForecastRun) -> dict[str, object]:
    return {
        "dataset_id": run.dataset_id,
        "dataset_name": run.dataset.original_filename,
        "product": run.product,
        "location": run.location,
        "category": run.category,
        "frequency": run.frequency,
    }


def _champion(run: ForecastRun) -> dict[str, object]:
    model = next((item for item in run.model_results if item.rank == 1), None)
    return {
        "model_name": run.champion_model,
        "reason": run.champion_reason,
        "metrics": model.metrics if model else {},
        "stability": model.stability if model else {},
        "parameters": model.parameters if model else {},
        "fold_count": len(model.folds) if model else 0,
    }


def _forecast_summary(run: ForecastRun) -> dict[str, object]:
    points = sorted(run.points, key=lambda item: item.timestamp)
    values = [point.forecast for point in points]
    first = values[0]
    last = values[-1]
    trajectory = (last - first) / first if first != 0 else None
    widths = [
        (point.upper_95 - point.lower_95) / abs(point.forecast)
        for point in points
        if point.lower_95 is not None and point.upper_95 is not None and point.forecast != 0
    ]
    return {
        "point_count": len(points),
        "first_value": first,
        "last_value": last,
        "total": round(sum(values), 6),
        "trajectory_delta": round(trajectory, 6) if trajectory is not None else None,
        "mean_relative_interval_width_95": (
            round(sum(widths) / len(widths), 6) if widths else None
        ),
        "first_period": points[0].timestamp.date().isoformat(),
        "last_period": points[-1].timestamp.date().isoformat(),
        "points": [
            {
                "timestamp": point.timestamp.date().isoformat(),
                "forecast": point.forecast,
                "lower_80": point.lower_80,
                "upper_80": point.upper_80,
                "lower_95": point.lower_95,
                "upper_95": point.upper_95,
            }
            for point in points
        ],
    }


def _safe_impacts(
    db: Session, signals: list[ContextSignal], decision_cutoff: datetime, run: ForecastRun
) -> dict[str, ContextImpactEstimate]:
    signal_ids = [signal.id for signal in signals]
    if not signal_ids:
        return {}
    estimates = (
        db.query(ContextImpactEstimate)
        .filter(
            ContextImpactEstimate.signal_id.in_(signal_ids),
            ContextImpactEstimate.status == "estimated",
            ContextImpactEstimate.estimated_at <= decision_cutoff,
            ContextImpactEstimate.data_cutoff <= _forecast_cutoff(run),
        )
        .order_by(ContextImpactEstimate.estimated_at.desc(), ContextImpactEstimate.id.desc())
        .all()
    )
    latest: dict[str, ContextImpactEstimate] = {}
    for estimate in estimates:
        latest.setdefault(estimate.signal_id, estimate)
    return latest


def _analogies(
    db: Session,
    future_signal: ContextSignal,
    decision_cutoff: datetime,
    run: ForecastRun,
) -> dict[str, object] | None:
    candidates = (
        db.query(ContextSignal)
        .filter(
            ContextSignal.dataset_id == future_signal.dataset_id,
            ContextSignal.id != future_signal.id,
            ContextSignal.signal_family == future_signal.signal_family,
            ContextSignal.signal_type == future_signal.signal_type,
            ContextSignal.event_start < future_signal.event_start,
            ContextSignal.available_at <= decision_cutoff,
            ContextSignal.status.notin_(["dismissed", "expired"]),
        )
        .all()
    )
    compatible = [item for item in candidates if scopes_are_compatible(future_signal, item)]
    impacts = _safe_impacts(db, compatible, decision_cutoff, run)
    values = [
        estimate.relative_delta
        for estimate in impacts.values()
        if estimate.relative_delta is not None
    ]
    if not values:
        return None
    return {
        "comparable_events": len(values),
        "minimum_relative_delta": min(values),
        "median_relative_delta": median(values),
        "maximum_relative_delta": max(values),
        "estimate_ids": sorted(estimate.id for estimate in impacts.values()),
        "descriptive_only": True,
    }


def collect_evidence(
    db: Session,
    forecast_run_id: str,
    scenario_run_id: str | None,
    decision_cutoff: datetime | None,
    scor_assessment_id: str | None = None,
    portfolio_run_id: str | None = None,
) -> dict[str, object]:
    forecast = require_forecast(db, forecast_run_id)
    if forecast.status != "completed" or not forecast.points or not forecast.champion_model:
        raise DataStudioError(
            "decision_forecast_unavailable",
            "El Forecast Run debe estar completado para generar recomendaciones.",
            409,
        )
    cutoff = _utc(decision_cutoff)
    if forecast.created_at > cutoff:
        raise DataStudioError(
            "decision_forecast_after_cutoff",
            "El Forecast Run aún no existía en la fecha de corte de decisión.",
            409,
        )
    scenario: ScenarioRun | None = None
    if scenario_run_id:
        scenario = require_scenario(db, scenario_run_id)
        if scenario.forecast_run_id != forecast.id:
            raise DataStudioError(
                "decision_scenario_mismatch",
                "El escenario no pertenece al Forecast Run seleccionado.",
                409,
            )
        if scenario.status != "completed" or not scenario.points:
            raise DataStudioError(
                "decision_scenario_unavailable",
                "El escenario debe estar ejecutado para analizar sus implicaciones.",
                409,
            )
        if scenario.created_at > cutoff or (scenario.executed_at and scenario.executed_at > cutoff):
            raise DataStudioError(
                "decision_scenario_after_cutoff",
                "El escenario aún no existía en la fecha de corte de decisión.",
                409,
            )

    context = SeriesContext(
        product=forecast.product, location=forecast.location, category=forecast.category
    )
    signals = (
        db.query(ContextSignal)
        .filter(
            or_(
                ContextSignal.dataset_id == forecast.dataset_id,
                ContextSignal.dataset_id.is_(None),
            ),
            ContextSignal.available_at <= cutoff,
            ContextSignal.status.notin_(["dismissed", "expired"]),
        )
        .order_by(ContextSignal.event_start, ContextSignal.id)
        .all()
    )
    relevant: list[ContextSignal] = []
    signal_snapshots: list[dict[str, object]] = []
    for signal in signals:
        matches, reasons = match_signal(signal, context)
        if not matches:
            continue
        relevant.append(signal)
        signal_snapshots.append(
            {
                "id": signal.id,
                "family": signal.signal_family,
                "type": signal.signal_type,
                "title": signal.title,
                "event_start": signal.event_start.isoformat(),
                "event_end": signal.event_end.isoformat() if signal.event_end else None,
                "available_at": signal.available_at.isoformat(),
                "confidence": signal.confidence,
                "knowledge_type": signal.knowledge_type,
                "status": signal.status,
                "match_reasons": reasons,
            }
        )
    impacts = _safe_impacts(db, relevant, cutoff, forecast)
    impact_snapshots = {
        signal_id: {
            "id": estimate.id,
            "relative_delta": estimate.relative_delta,
            "evidence_score": estimate.evidence_score,
            "evidence_level": estimate.evidence_level,
            "method": estimate.method,
            "event_periods": estimate.event_periods,
            "reference_periods": estimate.reference_periods,
            "estimated_at": estimate.estimated_at.isoformat(),
            "data_cutoff": estimate.data_cutoff.isoformat(),
            "association_not_causality": True,
        }
        for signal_id, estimate in impacts.items()
    }
    analogies = {
        signal.id: analogy
        for signal in relevant
        if signal.event_start > cutoff
        if (analogy := _analogies(db, signal, cutoff, forecast)) is not None
    }
    scenario_snapshot = None
    if scenario:
        scenario_snapshot = {
            "id": scenario.id,
            "name": scenario.name,
            "summary": scenario.summary_json,
            "warnings": scenario.warnings,
            "assumptions": [
                {
                    "id": item.id,
                    "type": item.assumption_type,
                    "label": item.label,
                    "source_type": item.source_type,
                    "magnitude": item.magnitude,
                    "start_at": item.start_at.isoformat(),
                    "end_at": item.end_at.isoformat() if item.end_at else None,
                }
                for item in sorted(scenario.assumptions, key=lambda item: item.order_index)
            ],
            "points": [
                {
                    "timestamp": point.timestamp.date().isoformat(),
                    "baseline": point.baseline,
                    "scenario": point.scenario,
                    "absolute_delta": point.absolute_delta,
                    "relative_delta": point.relative_delta,
                    "active_assumption_ids": point.active_assumption_ids,
                }
                for point in sorted(scenario.points, key=lambda item: item.timestamp)
            ],
            "hypothetical": True,
            "official_forecast_modified": False,
        }
    scor_assessments = list_available_scor_assessments(db, forecast, cutoff)
    scor_snapshot = (
        prepare_scor_evidence(db, forecast, scor_assessment_id, cutoff)
        if scor_assessment_id
        else None
    )
    portfolios = list_available_portfolios(db, forecast, cutoff)
    portfolio_snapshot = (
        prepare_portfolio_evidence(db, forecast, portfolio_run_id, cutoff)
        if portfolio_run_id
        else None
    )
    return {
        "forecast": forecast,
        "scenario": scenario,
        "decision_cutoff": cutoff,
        "selection": _selection(forecast),
        "champion": _champion(forecast),
        "forecast_summary": _forecast_summary(forecast),
        "signals": signal_snapshots,
        "impacts": impact_snapshots,
        "analogies": analogies,
        "scenario_snapshot": scenario_snapshot,
        "missing_operational_inputs": MISSING_OPERATIONAL_INPUTS,
        "scor_assessments": scor_assessments,
        "scor_snapshot": scor_snapshot,
        "portfolios": portfolios,
        "portfolio_snapshot": portfolio_snapshot,
    }
