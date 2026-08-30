"""Orchestrate auditable contextual association estimates without forecasting."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.context import ContextImpactEstimate, ContextSignal
from nexora_api.schemas.context_impact import ContextImpactEstimateRequest
from nexora_api.services.context.impact.analogies import (
    historical_analogy,
    scopes_are_compatible,
)
from nexora_api.services.context.impact.baseline import comparable_baseline
from nexora_api.services.context.impact.preparation import event_points, parse_points
from nexora_api.services.context.impact.scoring import evidence_score
from nexora_api.services.context.service import require_signal
from nexora_api.services.data_studio.storage import StorageService
from nexora_api.services.series.engine import build_series_profile

METHODS = {
    "daily": "weekday_matched_trailing_8_weeks",
    "weekly": "trailing_8_complete_periods",
    "monthly": "trailing_6_complete_periods",
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _cutoff_instant(value: date) -> datetime:
    return datetime.combine(value, time.max, UTC)


def _scope(signal: ContextSignal) -> dict[str, object]:
    values = {
        "scope_type": signal.scope_type,
        "product": signal.product,
        "category": signal.category,
        "location": signal.location,
        "channel": signal.channel,
        "market": signal.market,
        "country": signal.country,
        "region": signal.region,
    }
    return {key: value for key, value in values.items() if value is not None}


def _historical_comparable_count(db: Session, signal: ContextSignal, cutoff: date) -> int:
    candidates = (
        db.query(ContextSignal)
        .filter(
            ContextSignal.dataset_id == signal.dataset_id,
            ContextSignal.signal_family == signal.signal_family,
            ContextSignal.signal_type == signal.signal_type,
            ContextSignal.id != signal.id,
            ContextSignal.event_start < signal.event_start,
            ContextSignal.event_start <= _cutoff_instant(cutoff),
            ContextSignal.status.notin_(["dismissed", "expired"]),
        )
        .all()
    )
    return sum(scopes_are_compatible(signal, candidate) for candidate in candidates)


def _overlapping_signal_count(db: Session, signal: ContextSignal) -> int:
    event_end = signal.event_end or signal.event_start
    candidates = (
        db.query(ContextSignal)
        .filter(
            ContextSignal.dataset_id == signal.dataset_id,
            ContextSignal.id != signal.id,
            ContextSignal.status.notin_(["dismissed", "expired"]),
            ContextSignal.event_start <= event_end,
            or_(ContextSignal.event_end.is_(None), ContextSignal.event_end >= signal.event_start),
        )
        .all()
    )
    return len(candidates)


def _quality_summary(event: tuple, references: tuple, overlaps: int) -> dict[str, object]:
    combined = (*event, *references)
    contaminated_dates = {
        point.period
        for point in combined
        if point.demand is None
        or point.is_partial
        or any(point.events.get(code, 0) > 0 for code in ("missing", "outlier", "stockout"))
    }
    return {
        "missing_periods": sum(point.demand is None for point in combined),
        "outlier_observations": sum(point.events.get("outlier", 0) for point in combined),
        "possible_stockout_observations": sum(
            point.events.get("stockout", 0) for point in combined
        ),
        "partial_periods": sum(point.is_partial for point in combined),
        "contaminated_periods": len(contaminated_dates),
        "overlapping_signals": overlaps,
        "outliers_preserved": True,
        "missing_values_imputed": False,
    }


def _direction(relative_delta: float | None) -> str:
    if relative_delta is None:
        return "unknown"
    if abs(relative_delta) < 0.03:
        return "neutral"
    return "increase" if relative_delta > 0 else "decrease"


def serialize_estimate(estimate: ContextImpactEstimate) -> dict[str, object]:
    return {
        "id": estimate.id,
        "signal_id": estimate.signal_id,
        "dataset_id": estimate.dataset_id,
        "scope": estimate.scope_json,
        "frequency": estimate.frequency,
        "method": estimate.method,
        "status": estimate.status,
        "direction": estimate.direction,
        "baseline_value": estimate.baseline_value,
        "observed_value": estimate.observed_value,
        "absolute_delta": estimate.absolute_delta,
        "relative_delta": estimate.relative_delta,
        "sample_size": estimate.sample_size,
        "event_periods": estimate.event_periods,
        "reference_periods": estimate.reference_periods,
        "evidence_score": estimate.evidence_score,
        "evidence_level": estimate.evidence_level,
        "data_cutoff": estimate.data_cutoff,
        "availability_cutoff": estimate.availability_cutoff,
        "estimated_at": estimate.estimated_at,
        "reason_code": estimate.reason_code,
        "notes": estimate.notes,
        "evidence_breakdown": estimate.evidence_breakdown,
        "quality_summary": estimate.quality_summary,
        "input_snapshot": estimate.input_snapshot,
    }


def estimate_signal_impact(
    db: Session,
    signal_id: str,
    payload: ContextImpactEstimateRequest,
    storage: StorageService,
) -> ContextImpactEstimate:
    signal = require_signal(db, signal_id)
    if signal.dataset_id is None:
        raise DataStudioError(
            "impact_requires_dataset",
            "A contextual impact estimate requires a linked dataset.",
            409,
        )
    availability_cutoff = _utc(payload.availability_cutoff or datetime.now(UTC))
    profile = build_series_profile(
        db,
        signal.dataset_id,
        storage,
        product=signal.product,
        location=signal.location,
        category=signal.category,
        frequency=payload.frequency,
        end_date=payload.data_cutoff,
    )
    selection = profile["selection"]
    resolved_frequency = str(selection["resolved_frequency"])  # type: ignore[index]
    actual_cutoff = date.fromisoformat(str(selection["data_cutoff"]))  # type: ignore[index]
    points = parse_points(profile, actual_cutoff)
    selected_event = event_points(points, signal.event_start, signal.event_end, resolved_frequency)
    baseline = comparable_baseline(points, selected_event, resolved_frequency)
    overlaps = _overlapping_signal_count(db, signal)
    quality = _quality_summary(tuple(selected_event), baseline.references, overlaps)
    comparable_count = _historical_comparable_count(db, signal, actual_cutoff)
    score, level, breakdown = evidence_score(
        reference_periods=len(baseline.references),
        valid_event_periods=len(baseline.observed),
        expected_event_periods=baseline.expected_event_periods,
        contaminated_periods=int(quality["contaminated_periods"]),
        comparable_events=comparable_count,
        confidence=signal.confidence,
    )
    observed = baseline.observed_value
    baseline_value = baseline.baseline_value
    absolute_delta = (
        observed - baseline_value
        if observed is not None and baseline_value is not None
        else None
    )
    relative_delta = (
        absolute_delta / baseline_value
        if absolute_delta is not None and baseline_value not in {None, 0.0}
        else None
    )

    status = "estimated"
    reason: str | None = None
    notes = "Asociación descriptiva frente a un baseline comparable; no implica causalidad."
    if signal.status in {"dismissed", "expired"}:
        status, reason = "not_applicable", "inactive_signal"
    elif signal.knowledge_type == "scenario":
        status, reason = "not_applicable", "scenario_has_no_observed_outcome"
    elif signal.available_at > availability_cutoff:
        status, reason = "not_observable", "signal_unavailable_at_cutoff"
    elif signal.event_start.date() > actual_cutoff:
        status, reason = "not_observable", "event_after_data_cutoff"
    elif signal.event_end is not None and signal.event_end.date() > actual_cutoff:
        status, reason = "pending", "event_outcome_incomplete_at_data_cutoff"
    elif not selected_event or observed is None:
        status, reason = "not_observable", "no_observed_demand_for_event"
    elif signal.signal_type == "stockout":
        status, reason = "not_observable", "demand_censored_by_stockout"
        level = "insufficient"
        notes = (
            "La venta observada durante una ruptura de stock puede estar censurada y no "
            "representa la demanda real; no se transfiere como impacto esperado."
        )
    elif len(baseline.references) < 3:
        status, reason = "insufficient_evidence", "insufficient_reference_periods"
    elif baseline_value == 0:
        status, reason = "insufficient_evidence", "zero_baseline"
    elif level == "insufficient":
        status, reason = "insufficient_evidence", "evidence_score_below_threshold"

    estimate = ContextImpactEstimate(
        id=str(uuid4()),
        signal_id=signal.id,
        dataset_id=signal.dataset_id,
        scope_json=_scope(signal),
        frequency=resolved_frequency,
        method=METHODS.get(resolved_frequency, "trailing_complete_periods"),
        status=status,
        direction=_direction(relative_delta) if status == "estimated" else "unknown",
        baseline_value=round(baseline_value, 6) if baseline_value is not None else None,
        observed_value=round(observed, 6) if observed is not None else None,
        absolute_delta=round(absolute_delta, 6) if absolute_delta is not None else None,
        relative_delta=round(relative_delta, 6) if relative_delta is not None else None,
        sample_size=len(baseline.references) + len(baseline.observed),
        event_periods=len(baseline.observed),
        reference_periods=len(baseline.references),
        evidence_score=score,
        evidence_level=level,
        data_cutoff=_cutoff_instant(actual_cutoff),
        availability_cutoff=availability_cutoff,
        reason_code=reason,
        notes=notes,
        evidence_breakdown=breakdown,
        quality_summary=quality,
        input_snapshot={
            "signal": {
                "event_start": signal.event_start.isoformat(),
                "event_end": signal.event_end.isoformat() if signal.event_end else None,
                "available_at": signal.available_at.isoformat(),
                "knowledge_type": signal.knowledge_type,
                "confidence": signal.confidence,
            },
            "series": {
                "frequency": resolved_frequency,
                "data_cutoff": actual_cutoff.isoformat(),
                "product": signal.product,
                "category": signal.category,
                "location": signal.location,
            },
            "comparable_historical_events": comparable_count,
            "overlapping_signals": overlaps,
        },
    )
    signal.impact_status = status
    db.add(estimate)
    db.commit()
    db.refresh(estimate)
    return estimate


def latest_signal_estimate(db: Session, signal_id: str) -> ContextImpactEstimate | None:
    require_signal(db, signal_id)
    return (
        db.query(ContextImpactEstimate)
        .filter(ContextImpactEstimate.signal_id == signal_id)
        .order_by(ContextImpactEstimate.estimated_at.desc(), ContextImpactEstimate.id.desc())
        .first()
    )


def list_dataset_estimates(db: Session, dataset_id: str) -> list[ContextImpactEstimate]:
    ordered = (
        db.query(ContextImpactEstimate)
        .filter(ContextImpactEstimate.dataset_id == dataset_id)
        .order_by(ContextImpactEstimate.estimated_at.desc(), ContextImpactEstimate.id.desc())
        .all()
    )
    latest: dict[str, ContextImpactEstimate] = {}
    for estimate in ordered:
        latest.setdefault(estimate.signal_id, estimate)
    return list(latest.values())


def get_signal_analogies(db: Session, signal_id: str) -> dict[str, object]:
    return historical_analogy(db, require_signal(db, signal_id))
