"""Empirical future intervals derived from out-of-sample residuals."""

from __future__ import annotations

import numpy as np

MIN_INTERVAL_ERRORS = 20


def empirical_intervals(
    forecast: np.ndarray, residuals: list[float], minimum_errors: int = MIN_INTERVAL_ERRORS
) -> dict[str, list[float | None] | int | str]:
    """Add pooled residual quantiles to forecasts without parametric claims."""
    valid = np.asarray([value for value in residuals if np.isfinite(value)], dtype=float)
    if len(valid) < minimum_errors:
        empty: list[float | None] = [None] * len(forecast)
        return {
            "method": "insufficient_out_of_sample_errors",
            "residual_count": int(len(valid)),
            "lower_80": empty.copy(),
            "upper_80": empty.copy(),
            "lower_95": empty.copy(),
            "upper_95": empty.copy(),
        }
    q025, q10, q90, q975 = np.quantile(valid, [0.025, 0.10, 0.90, 0.975])
    return {
        "method": "pooled_out_of_sample_residual_quantiles",
        "residual_count": int(len(valid)),
        "lower_80": [round(float(value + q10), 6) for value in forecast],
        "upper_80": [round(float(value + q90), 6) for value in forecast],
        "lower_95": [round(float(value + q025), 6) for value in forecast],
        "upper_95": [round(float(value + q975), 6) for value in forecast],
    }
