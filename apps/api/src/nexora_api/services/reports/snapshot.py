"""Freeze report inputs without recalculating any upstream result."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from nexora_api.models.dataset import Dataset, ForecastRun
from nexora_api.models.decision import DecisionRun
from nexora_api.models.explanation import ExplanationRun
from nexora_api.models.portfolio import PortfolioRun
from nexora_api.models.scenario import ScenarioRun
from nexora_api.models.scor import ScorAssessmentRun
from nexora_api.services.decisions.service import serialize_run as serialize_decision
from nexora_api.services.explanations.service import serialize_run as serialize_explanation
from nexora_api.services.portfolio.service import serialize_portfolio
from nexora_api.services.scenarios.service import serialize_scenario
from nexora_api.services.scor.service import serialize_assessment


def json_safe(value: object) -> object:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def _forecast(run: ForecastRun) -> dict[str, object]:
    models = sorted(
        run.model_results, key=lambda item: (item.rank is None, item.rank or 999, item.model_name)
    )
    return {
        "id": run.id,
        "dataset_id": run.dataset_id,
        "selection": {
            "product": run.product,
            "location": run.location,
            "category": run.category,
        },
        "frequency": run.frequency,
        "horizon": run.requested_horizon,
        "validation_horizon": run.validation_horizon,
        "created_at": run.created_at,
        "data_cutoff": run.data_cutoff,
        "training_cutoff": run.preprocessing_summary.get("training_cutoff"),
        "preprocessing": run.preprocessing_summary,
        "seasonality_candidate": run.seasonality_candidate,
        "seasonality_evidence": run.seasonality_evidence,
        "status": run.status,
        "champion_model": run.champion_model,
        "champion_reason": run.champion_reason,
        "warnings": run.warnings,
        "models": [
            {
                "id": model.id,
                "model_name": model.model_name,
                "eligible": model.eligible,
                "status": model.status,
                "failure_reason": model.failure_reason,
                "parameters": model.parameters,
                "metrics": model.metrics,
                "stability": model.stability,
                "rank": model.rank,
                "folds": [
                    {
                        "fold_index": fold.fold_index,
                        "train_start": fold.train_start,
                        "train_end": fold.train_end,
                        "validation_start": fold.validation_start,
                        "validation_end": fold.validation_end,
                        "training_observations": fold.training_observations,
                        "validation_observations": fold.validation_observations,
                        "metrics": fold.metrics,
                    }
                    for fold in sorted(model.folds, key=lambda item: item.fold_index)
                ],
            }
            for model in models
        ],
        "forecast_points": [
            {
                "timestamp": point.timestamp,
                "forecast": point.forecast,
                "lower_80": point.lower_80,
                "upper_80": point.upper_80,
                "lower_95": point.lower_95,
                "upper_95": point.upper_95,
            }
            for point in sorted(run.points, key=lambda item: item.timestamp)
        ],
        "recalculated": False,
    }


def freeze_sources(db: Session, resolved: dict[str, object | None]) -> dict[str, object]:
    forecast = resolved["forecast"]
    scenario = resolved["scenario"]
    scor = resolved["scor"]
    portfolio = resolved["portfolio"]
    decision = resolved["decision"]
    explanation = resolved["explanation"]
    dataset_id = resolved["dataset_id"]
    dataset = db.get(Dataset, dataset_id) if dataset_id else None
    return json_safe(
        {
            "dataset": {
                "id": dataset.id,
                "name": dataset.original_filename,
                "status": dataset.status,
                "frequency": dataset.frequency,
                "readiness_score": dataset.readiness_score,
                "imported_at": dataset.imported_at,
            }
            if dataset
            else None,
            "forecast": _forecast(forecast) if isinstance(forecast, ForecastRun) else None,
            "scenario": serialize_scenario(scenario) if isinstance(scenario, ScenarioRun) else None,
            "scor": serialize_assessment(scor) if isinstance(scor, ScorAssessmentRun) else None,
            "portfolio": serialize_portfolio(portfolio)
            if isinstance(portfolio, PortfolioRun)
            else None,
            "decision": serialize_decision(decision) if isinstance(decision, DecisionRun) else None,
            "explanation": serialize_explanation(explanation)
            if isinstance(explanation, ExplanationRun)
            else None,
        }
    )  # type: ignore[return-value]
