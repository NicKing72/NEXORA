"""Validate scope and contextual provenance for scenario assumptions."""

from __future__ import annotations

from datetime import UTC, datetime, time

from sqlalchemy.orm import Session

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.context import ContextImpactEstimate, ContextSignal
from nexora_api.models.dataset import ForecastRun
from nexora_api.schemas.scenario import ScenarioAssumptionInput
from nexora_api.services.context.relevance import SeriesContext, match_signal


def _series_context(run: ForecastRun) -> SeriesContext:
    return SeriesContext(product=run.product, category=run.category, location=run.location)


def validate_scope(scope: dict[str, object], run: ForecastRun) -> None:
    selected = {"product": run.product, "category": run.category, "location": run.location}
    for dimension, expected in scope.items():
        if dimension not in selected or expected is None:
            continue
        actual = selected[dimension]
        if actual is None or str(actual).casefold() != str(expected).casefold():
            raise DataStudioError(
                "scenario_scope_mismatch",
                f"El supuesto no coincide con la dimensión {dimension} del baseline.",
                409,
            )


def context_provenance(
    db: Session, payload: ScenarioAssumptionInput, run: ForecastRun
) -> tuple[dict[str, object], list[str]]:
    if payload.assumption_type != "context_impact":
        return {
            "kind": "user_hypothesis",
            "source_note": payload.source_note,
            "causal_claim": False,
        }, []
    estimate = db.get(ContextImpactEstimate, payload.context_impact_estimate_id)
    signal = db.get(ContextSignal, payload.context_signal_id)
    if estimate is None or signal is None or estimate.signal_id != signal.id:
        raise DataStudioError(
            "scenario_context_evidence_not_found",
            "No existe una estimación contextual compatible con la señal indicada.",
            404,
        )
    if estimate.status != "estimated" or estimate.relative_delta is None:
        raise DataStudioError(
            "scenario_context_evidence_insufficient",
            "La señal no dispone de evidencia histórica estimada utilizable.",
            409,
        )
    cutoff = datetime.combine(run.data_cutoff.date(), time.max, UTC)
    if signal.available_at > cutoff:
        raise DataStudioError(
            "scenario_context_evidence_after_cutoff",
            "La evidencia contextual no estaba disponible en el corte del Forecast Run.",
            409,
        )
    if estimate.data_cutoff > cutoff:
        raise DataStudioError(
            "scenario_context_data_after_cutoff",
            "La estimación contextual utiliza demanda posterior al corte del Forecast Run.",
            409,
        )
    matches, reasons = match_signal(signal, _series_context(run))
    if not matches:
        raise DataStudioError(
            "scenario_context_scope_mismatch",
            "La señal contextual no aplica al alcance de la serie del baseline.",
            409,
        )
    if abs(float(payload.magnitude) - estimate.relative_delta) > 1e-9:
        raise DataStudioError(
            "scenario_context_magnitude_mismatch",
            "La magnitud debe coincidir con la estimación histórica persistida.",
            409,
        )
    warnings = [
        "historical_association_not_causal",
        "context_impact_not_applied_to_official_forecast",
    ]
    return {
        "kind": "historical_evidence",
        "signal_id": signal.id,
        "signal_title": signal.title,
        "impact_estimate_id": estimate.id,
        "historical_relative_delta": estimate.relative_delta,
        "evidence_score": estimate.evidence_score,
        "evidence_level": estimate.evidence_level,
        "event_periods": estimate.event_periods,
        "reference_periods": estimate.reference_periods,
        "historical_baseline": estimate.baseline_value,
        "method": estimate.method,
        "availability_cutoff": estimate.availability_cutoff.isoformat(),
        "data_cutoff": estimate.data_cutoff.isoformat(),
        "match_reasons": reasons,
        "causal_claim": False,
    }, warnings
