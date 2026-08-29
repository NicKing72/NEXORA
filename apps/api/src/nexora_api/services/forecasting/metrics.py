"""Forecast metrics calculated from aligned out-of-sample observations."""

from __future__ import annotations

import math

import numpy as np


def _finite_pairs(
    actual: list[float] | np.ndarray, forecast: list[float] | np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    actual_array = np.asarray(actual, dtype=float)
    forecast_array = np.asarray(forecast, dtype=float)
    if actual_array.shape != forecast_array.shape:
        raise ValueError("Actual and forecast arrays must have the same shape.")
    valid = np.isfinite(actual_array) & np.isfinite(forecast_array)
    return actual_array[valid], forecast_array[valid]


def calculate_metrics(
    actual: list[float] | np.ndarray, forecast: list[float] | np.ndarray
) -> dict[str, float | int | None]:
    """Return metrics using the documented forecast-minus-actual bias convention."""
    observed, predicted = _finite_pairs(actual, forecast)
    count = int(len(observed))
    if count == 0:
        return {
            "observations": 0,
            "mae": None,
            "rmse": None,
            "mape": None,
            "smape": None,
            "wmape": None,
            "bias": None,
            "bias_percent": None,
        }
    error = predicted - observed
    absolute_error = np.abs(error)
    mae = float(np.mean(absolute_error))
    rmse = float(math.sqrt(float(np.mean(np.square(error)))))
    has_zero_actual = bool(np.any(observed == 0))
    mape = None if has_zero_actual else float(np.mean(absolute_error / np.abs(observed)))
    smape_denominator = np.abs(observed) + np.abs(predicted)
    smape_terms = np.divide(
        2 * absolute_error,
        smape_denominator,
        out=np.zeros_like(absolute_error),
        where=smape_denominator != 0,
    )
    actual_weight = float(np.sum(np.abs(observed)))
    actual_sum = float(np.sum(observed))
    return {
        "observations": count,
        "mae": round(mae, 6),
        "rmse": round(rmse, 6),
        "mape": None if mape is None else round(mape, 6),
        "smape": round(float(np.mean(smape_terms)), 6),
        "wmape": None
        if actual_weight == 0
        else round(float(np.sum(absolute_error)) / actual_weight, 6),
        "bias": round(float(np.mean(error)), 6),
        "bias_percent": None
        if abs(actual_sum) < 1e-12
        else round(float(np.sum(error)) / actual_sum, 6),
    }


def stability_from_folds(fold_metrics: list[dict[str, object]]) -> dict[str, object]:
    """Classify WMAPE variability; lower cross-fold CV means greater stability."""
    values = np.asarray(
        [metric["wmape"] for metric in fold_metrics if metric.get("wmape") is not None],
        dtype=float,
    )
    if len(values) < 2:
        return {"label": "insufficient", "wmape_cv": None, "wmape_std": None}
    mean = float(values.mean())
    deviation = float(values.std(ddof=0))
    coefficient = deviation / mean if mean > 1e-12 else 0.0 if deviation == 0 else None
    if coefficient is None:
        label = "low"
    elif coefficient <= 0.10:
        label = "high"
    elif coefficient <= 0.25:
        label = "moderate"
    else:
        label = "low"
    return {
        "label": label,
        "wmape_cv": None if coefficient is None else round(coefficient, 6),
        "wmape_std": round(deviation, 6),
    }
