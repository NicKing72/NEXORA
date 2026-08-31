"""Prepare immutable evidence from a persisted ForecastRun and optional layers."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import Dataset, ForecastRun
from nexora_api.services.explanations.comparison import (
    backtesting_snapshot,
    comparison_snapshot,
)
from nexora_api.services.explanations.decision_context import prepare_layers
from nexora_api.services.explanations.forecast_explanation import forecast_snapshot
from nexora_api.services.explanations.model_explanation import explain_model
from nexora_api.services.forecasting.service import require_run as require_forecast_run


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _parse_cutoff(value: object) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return _utc(parsed)


def _series_id(run: ForecastRun) -> str:
    return "|".join(
        [
            run.dataset_id,
            f"product={run.product or '*'}",
            f"location={run.location or '*'}",
            f"category={run.category or '*'}",
            f"frequency={run.frequency}",
        ]
    )


def _limitations(
    run: ForecastRun,
    champion: object,
    output: dict[str, object],
    layers: dict[str, object],
) -> list[str]:
    limitations: list[str] = []
    preprocessing = run.preprocessing_summary or {}
    if not preprocessing.get("training_cutoff"):
        limitations.append("training_cutoff_not_persisted")
    if not preprocessing.get("calculation_version"):
        limitations.append("forecast_core_version_not_persisted")
    if not getattr(champion, "parameters", None):
        limitations.append("model_parameters_not_persisted")
    summary = output["summary"]
    if not summary.get("has_80_interval") and not summary.get("has_95_interval"):
        limitations.append("forecast_intervals_unavailable")
    if preprocessing.get("missing_before", 0):
        limitations.append("training_history_had_missing_values")
    if preprocessing.get("excluded_partial_periods", 0):
        limitations.append("partial_periods_excluded")
    if run.seasonality_evidence in {"low", "insufficient", "inconclusive"}:
        limitations.append("seasonality_evidence_limited")
    if not any(layers.get(key) for key in ("scenario", "scor", "portfolio", "decision")):
        limitations.append("downstream_context_not_included")
    limitations.append("historical_association_is_not_causality")
    limitations.append("forecast_does_not_guarantee_future_demand")
    return list(dict.fromkeys(limitations))


def prepare_snapshot(
    db: Session,
    *,
    forecast_run_id: str,
    cutoff: datetime | None,
    scenario_run_id: str | None,
    scor_assessment_id: str | None,
    portfolio_run_id: str | None,
    decision_run_id: str | None,
) -> dict[str, object]:
    run = require_forecast_run(db, forecast_run_id)
    if run.status != "completed" or not run.champion_model:
        raise DataStudioError(
            "explanation_forecast_incomplete",
            "Only a completed forecast run with a Champion can be explained.",
            409,
        )
    explanation_cutoff = _utc(cutoff or datetime.now(UTC))
    if _utc(run.created_at) > explanation_cutoff:
        raise DataStudioError(
            "explanation_future_forecast",
            "The forecast run was not available at the explanation cutoff.",
            409,
        )
    training_cutoff = _parse_cutoff((run.preprocessing_summary or {}).get("training_cutoff"))
    if training_cutoff is not None and training_cutoff > explanation_cutoff:
        raise DataStudioError(
            "explanation_future_training_data",
            "The forecast training cutoff exceeds the explanation cutoff.",
            409,
        )
    if _utc(run.data_cutoff) > explanation_cutoff:
        raise DataStudioError(
            "explanation_future_training_data",
            "The forecast data cutoff exceeds the explanation cutoff.",
            409,
        )
    dataset = db.query(Dataset).filter(Dataset.id == run.dataset_id).one()
    champion = next(
        (item for item in run.model_results if item.model_name == run.champion_model), None
    )
    if champion is None:
        raise DataStudioError(
            "explanation_champion_missing",
            "The persisted Champion result is not available.",
            409,
        )
    layers = prepare_layers(
        db,
        forecast_run_id=run.id,
        dataset_id=run.dataset_id,
        cutoff=explanation_cutoff,
        scenario_run_id=scenario_run_id,
        scor_assessment_id=scor_assessment_id,
        portfolio_run_id=portfolio_run_id,
        decision_run_id=decision_run_id,
    )
    comparison = comparison_snapshot(run)
    backtesting = backtesting_snapshot(run)
    output = forecast_snapshot(run)
    champion_snapshot = {
        "model_name": champion.model_name,
        "reason": run.champion_reason,
        "rank": champion.rank,
        "metrics": dict(champion.metrics or {}),
        "stability": dict(champion.stability or {}),
        "explanation": explain_model(champion),
    }
    scope = {
        "dataset_id": run.dataset_id,
        "dataset_name": dataset.original_filename,
        "series_id": _series_id(run),
        "product": run.product,
        "location": run.location,
        "category": run.category,
        "frequency": run.frequency,
        "horizon": run.requested_horizon,
    }
    limitations = _limitations(run, champion, output, layers)
    return {
        "forecast_run": run,
        "cutoff": explanation_cutoff,
        "series_id": scope["series_id"],
        "scope": scope,
        "dataset": {
            "id": dataset.id,
            "name": dataset.original_filename,
            "source_type": dataset.source_type,
            "rows": dataset.row_count,
            "columns": dataset.column_count,
            "readiness_score": dataset.readiness_score,
            "imported_at": dataset.imported_at.isoformat(),
        },
        "forecast": {
            "id": run.id,
            "created_at": run.created_at.isoformat(),
            "data_cutoff": run.data_cutoff.date().isoformat(),
            "training_cutoff": (run.preprocessing_summary or {}).get("training_cutoff"),
            "frequency": run.frequency,
            "horizon": run.requested_horizon,
            "validation_horizon": run.validation_horizon,
            "seasonality_candidate": run.seasonality_candidate,
            "seasonality_evidence": run.seasonality_evidence,
            "preprocessing": dict(run.preprocessing_summary or {}),
            "warnings": list(run.warnings or []),
            "calculation_version": (run.preprocessing_summary or {}).get(
                "calculation_version"
            ),
        },
        "champion": champion_snapshot,
        "comparison": comparison,
        "backtesting": backtesting,
        "forecast_output": output,
        "layers": layers,
        "limitations": limitations,
        "warnings": list(run.warnings or []),
        "created_from": "decision" if decision_run_id else "manual",
    }
