"""Leakage-safe expanding-window backtesting."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from nexora_api.services.forecasting.metrics import calculate_metrics, stability_from_folds
from nexora_api.services.forecasting.models import (
    MODEL_NAMES,
    ModelNotEligible,
    fit_and_forecast,
    model_eligibility,
)

VALIDATION_CAPS = {"daily": 14, "weekly": 8, "monthly": 6}
MAX_FOLDS = 5


@dataclass(frozen=True)
class FoldWindow:
    index: int
    train_end: int
    validation_end: int


def validation_horizon_for(frequency: str, requested_horizon: int) -> int:
    return min(requested_horizon, VALIDATION_CAPS.get(frequency, 6))


def build_fold_windows(length: int, validation_horizon: int) -> list[FoldWindow]:
    """Return non-overlapping validation blocks with expanding training prefixes."""
    minimum_training = max(5, validation_horizon)
    possible = max(0, (length - minimum_training) // validation_horizon)
    folds = min(MAX_FOLDS, possible)
    first_validation = length - folds * validation_horizon
    return [
        FoldWindow(
            index=index + 1,
            train_end=first_validation + index * validation_horizon,
            validation_end=first_validation + (index + 1) * validation_horizon,
        )
        for index in range(folds)
    ]


def assess_model_backtest_evaluability(
    model_name: str,
    series: pd.Series,
    *,
    frequency: str,
    requested_horizon: int,
    seasonal_period: int | None,
    seasonal_eligible: bool,
) -> dict[str, object]:
    """Describe whether existing folds can evaluate a final-fit-eligible model."""
    validation_horizon = validation_horizon_for(frequency, requested_horizon)
    windows = build_fold_windows(len(series), validation_horizon)
    if not windows:
        return {
            "evaluable": False,
            "reason": "insufficient_backtest_history",
            "evaluable_folds": 0,
            "total_folds": 0,
        }
    evaluable_folds = 0
    reasons: list[str] = []
    for window in windows:
        train = series.iloc[: window.train_end]
        eligible, reason = model_eligibility(
            model_name,
            train,
            frequency=frequency,
            seasonal_period=seasonal_period,
            seasonal_eligible=seasonal_eligible,
            continuous=bool(not train.isna().any()),
        )
        if eligible:
            evaluable_folds += 1
        elif reason:
            reasons.append(reason)
    reason: str | None = None
    if evaluable_folds == 0:
        if model_name.startswith("holt_winters") and reasons and all(
            item == "insufficient_seasonal_history" for item in reasons
        ):
            reason = "insufficient_fold_seasonal_history"
        else:
            reason = reasons[0] if reasons else "no_valid_folds"
    return {
        "evaluable": evaluable_folds > 0,
        "reason": reason,
        "evaluable_folds": evaluable_folds,
        "total_folds": len(windows),
    }


def evaluate_models(
    series: pd.Series,
    *,
    frequency: str,
    requested_horizon: int,
    seasonal_period: int | None,
    seasonal_eligible: bool,
    continuous: bool,
) -> tuple[list[dict[str, object]], int]:
    validation_horizon = validation_horizon_for(frequency, requested_horizon)
    windows = build_fold_windows(len(series), validation_horizon)
    results: list[dict[str, object]] = []
    for model_name in MODEL_NAMES:
        eligible, reason = model_eligibility(
            model_name,
            series,
            frequency=frequency,
            seasonal_period=seasonal_period,
            seasonal_eligible=seasonal_eligible,
            continuous=continuous,
        )
        result: dict[str, object] = {
            "model_name": model_name,
            "eligible": eligible,
            "status": "not_eligible" if not eligible else "pending",
            "failure_reason": reason,
            "parameters": (
                {"seasonal_period": seasonal_period}
                if model_name
                in {
                    "seasonal_naive",
                    "holt_winters_additive",
                    "holt_winters_multiplicative",
                }
                and seasonal_period is not None
                else {}
            ),
            "metrics": {},
            "stability": {"label": "insufficient", "wmape_cv": None, "wmape_std": None},
            "folds": [],
            "residuals": [],
        }
        if not eligible:
            results.append(result)
            continue
        if not windows:
            result.update(status="not_evaluable", failure_reason="insufficient_backtest_history")
            results.append(result)
            continue
        all_actual: list[float] = []
        all_forecast: list[float] = []
        residuals: list[float] = []
        fold_results: list[dict[str, object]] = []
        fold_ineligible: list[str] = []
        fold_failures: list[str] = []
        for window in windows:
            train = series.iloc[: window.train_end].copy(deep=True)
            validation = series.iloc[window.train_end : window.validation_end].copy(deep=True)
            try:
                fitted = fit_and_forecast(
                    model_name,
                    train,
                    len(validation),
                    frequency=frequency,
                    seasonal_period=seasonal_period,
                    seasonal_eligible=seasonal_eligible,
                    continuous=bool(not train.isna().any()),
                )
            except ModelNotEligible as error:
                fold_ineligible.append(str(error))
                continue
            except (RuntimeError, ValueError, ArithmeticError) as error:
                fold_failures.append(str(error))
                continue
            actual = validation.to_numpy(dtype=float)
            forecast = fitted.values
            metrics = calculate_metrics(actual, forecast)
            valid = np.isfinite(actual) & np.isfinite(forecast)
            all_actual.extend(actual[valid].tolist())
            all_forecast.extend(forecast[valid].tolist())
            residuals.extend((actual[valid] - forecast[valid]).tolist())
            fold_results.append(
                {
                    "fold_index": window.index,
                    "train_start": train.index[0],
                    "train_end": train.index[-1],
                    "validation_start": validation.index[0],
                    "validation_end": validation.index[-1],
                    "training_observations": int(len(train)),
                    "validation_observations": int(len(validation)),
                    "metrics": metrics,
                    "actual_values": [
                        None if not np.isfinite(value) else round(float(value), 6)
                        for value in actual
                    ],
                    "forecast_values": [round(float(value), 6) for value in forecast],
                    "parameters": fitted.parameters,
                }
            )
        if not fold_results:
            backtest_reason = fold_failures[0] if fold_failures else None
            if backtest_reason is None and fold_ineligible:
                backtest_reason = fold_ineligible[0]
                if model_name.startswith("holt_winters") and all(
                    item == "insufficient_seasonal_history" for item in fold_ineligible
                ):
                    backtest_reason = "insufficient_fold_seasonal_history"
            result.update(
                status="failed" if fold_failures else "not_evaluable",
                failure_reason=backtest_reason or "no_valid_folds",
            )
            results.append(result)
            continue
        fold_metrics = [fold["metrics"] for fold in fold_results]
        result.update(
            status="succeeded",
            failure_reason=(
                "some_folds_failed"
                if fold_failures
                else "some_folds_not_evaluable"
                if fold_ineligible
                else None
            ),
            parameters=fold_results[-1]["parameters"],
            metrics=calculate_metrics(all_actual, all_forecast),
            stability=stability_from_folds(fold_metrics),
            folds=fold_results,
            residuals=residuals,
        )
        results.append(result)
    return results, validation_horizon
