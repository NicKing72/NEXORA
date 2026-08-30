"""Strict-scope historical analogies for future contextual signals."""

from __future__ import annotations

from statistics import median

from sqlalchemy.orm import Session

from nexora_api.models.context import ContextImpactEstimate, ContextSignal

SCOPE_DIMENSIONS = (
    "country",
    "region",
    "product",
    "category",
    "location",
    "channel",
    "market",
)


def scopes_are_compatible(left: ContextSignal, right: ContextSignal) -> bool:
    return left.scope_type == right.scope_type and all(
        getattr(left, dimension) == getattr(right, dimension)
        for dimension in SCOPE_DIMENSIONS
    )


def historical_analogy(db: Session, signal: ContextSignal) -> dict[str, object]:
    if signal.knowledge_type not in {"known_future", "forecasted_external", "scenario"}:
        return {
            "signal_id": signal.id,
            "status": "not_applicable",
            "comparable_events": 0,
            "estimate_ids": [],
            "reason_code": "signal_is_not_future_context",
            "notes": "La señal no representa contexto futuro para transferir por analogía.",
        }
    candidates = (
        db.query(ContextImpactEstimate, ContextSignal)
        .join(ContextSignal, ContextSignal.id == ContextImpactEstimate.signal_id)
        .filter(
            ContextImpactEstimate.dataset_id == signal.dataset_id,
            ContextImpactEstimate.status == "estimated",
            ContextImpactEstimate.relative_delta.is_not(None),
            ContextSignal.signal_family == signal.signal_family,
            ContextSignal.signal_type == signal.signal_type,
            ContextSignal.id != signal.id,
            ContextSignal.event_start < signal.event_start,
            ContextImpactEstimate.data_cutoff <= signal.available_at,
        )
        .order_by(ContextImpactEstimate.estimated_at.desc())
        .all()
    )
    latest_by_signal: dict[str, tuple[ContextImpactEstimate, ContextSignal]] = {}
    for estimate, candidate in candidates:
        if candidate.id not in latest_by_signal and scopes_are_compatible(signal, candidate):
            latest_by_signal[candidate.id] = (estimate, candidate)
    comparable = list(latest_by_signal.values())
    if not comparable:
        return {
            "signal_id": signal.id,
            "status": "insufficient_evidence",
            "comparable_events": len(comparable),
            "estimate_ids": [estimate.id for estimate, _ in comparable],
            "reason_code": "insufficient_historical_analogies",
            "notes": (
                "Sin evidencia histórica suficiente: no existe un evento compatible "
                "estimado y disponible antes de esta señal."
            ),
        }
    values = sorted(float(estimate.relative_delta) for estimate, _ in comparable)
    return {
        "signal_id": signal.id,
        "status": "available",
        "comparable_events": len(values),
        "minimum_relative_delta": round(values[0], 6),
        "median_relative_delta": round(float(median(values)), 6),
        "maximum_relative_delta": round(values[-1], 6),
        "estimate_ids": [estimate.id for estimate, _ in comparable],
        "reason_code": None,
        "notes": (
            "Rango descriptivo de asociaciones observadas en eventos históricos "
            "compatibles; no modifica el pronóstico."
        ),
    }
