"""Reconstruct persisted model comparison without reranking or retraining."""

from __future__ import annotations

from statistics import fmean, pstdev

from nexora_api.models.dataset import ForecastRun
from nexora_api.services.explanations.model_explanation import explain_model
from nexora_api.services.forecasting.ranking import WMAPE_TIE_TOLERANCE


def _number(value: object) -> float | int | None:
    return value if isinstance(value, (int, float)) else None


def comparison_snapshot(run: ForecastRun) -> list[dict[str, object]]:
    models = sorted(
        run.model_results,
        key=lambda item: (item.rank is None, item.rank or 999, item.model_name),
    )
    champion = next((item for item in models if item.model_name == run.champion_model), None)
    champion_wmape = (
        _number((champion.metrics or {}).get("wmape")) if champion is not None else None
    )
    return [
        {
            "id": model.id,
            "model_name": model.model_name,
            "status": model.status,
            "eligible": model.eligible,
            "rank": model.rank,
            "selection_score": _number((model.metrics or {}).get("wmape")),
            "metrics": dict(model.metrics or {}),
            "stability": dict(model.stability or {}),
            "parameters": dict(model.parameters or {}),
            "valid_folds": len(model.folds),
            "observations": (model.metrics or {}).get("observations"),
            "is_champion": model.model_name == run.champion_model,
            "within_champion_tolerance": bool(
                champion_wmape is not None
                and _number((model.metrics or {}).get("wmape")) is not None
                and abs(float((model.metrics or {})["wmape"]) - float(champion_wmape))
                < WMAPE_TIE_TOLERANCE
            ),
            "failure_reason": model.failure_reason,
            "explanation": explain_model(model),
        }
        for model in models
    ]


def backtesting_snapshot(run: ForecastRun) -> dict[str, object]:
    champion = next(
        (item for item in run.model_results if item.model_name == run.champion_model), None
    )
    if champion is None:
        return {"champion_model": run.champion_model, "folds": [], "summary": {}}
    folds = sorted(champion.folds, key=lambda item: item.fold_index)
    wmape_values = [
        float(item.metrics["wmape"])
        for item in folds
        if (item.metrics or {}).get("wmape") is not None
    ]
    serialized = [
        {
            "fold_index": item.fold_index,
            "train_start": item.train_start.date().isoformat(),
            "train_end": item.train_end.date().isoformat(),
            "validation_start": item.validation_start.date().isoformat(),
            "validation_end": item.validation_end.date().isoformat(),
            "training_observations": item.training_observations,
            "validation_observations": item.validation_observations,
            "metrics": dict(item.metrics or {}),
        }
        for item in folds
    ]
    return {
        "champion_model": champion.model_name,
        "folds": serialized,
        "summary": {
            "fold_count": len(folds),
            "mean_wmape": round(fmean(wmape_values), 6) if wmape_values else None,
            "wmape_dispersion": round(pstdev(wmape_values), 6)
            if len(wmape_values) > 1
            else None,
            "persisted_metrics": dict(champion.metrics or {}),
            "persisted_stability": dict(champion.stability or {}),
        },
    }
