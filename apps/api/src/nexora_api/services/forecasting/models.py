"""Small deterministic model adapter registry for Forecast Core v1."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing, Holt, SimpleExpSmoothing
except ImportError:  # pragma: no cover - depends on host native-library policy
    ExponentialSmoothing = Holt = SimpleExpSmoothing = None  # type: ignore[assignment,misc]

MODEL_NAMES = (
    "naive",
    "seasonal_naive",
    "moving_average",
    "ses",
    "holt",
    "holt_winters_additive",
    "holt_winters_multiplicative",
)
MOVING_AVERAGE_WINDOWS = {"daily": 7, "weekly": 4, "monthly": 3}
NUMPY_HW_PARAMETER_GRID = (0.2, 0.4, 0.6, 0.8)


class ModelNotEligible(ValueError):
    """A transparent data requirement prevents fitting a model."""


@dataclass(frozen=True)
class FittedForecast:
    values: np.ndarray
    parameters: dict[str, object]


def model_eligibility(
    model_name: str,
    series: pd.Series,
    *,
    frequency: str,
    seasonal_period: int | None,
    seasonal_eligible: bool,
    continuous: bool,
) -> tuple[bool, str | None]:
    values = pd.to_numeric(series, errors="coerce")
    valid_count = int(values.notna().sum())
    if valid_count == 0:
        return False, "no_valid_training_values"
    if model_name == "seasonal_naive":
        if seasonal_period is None:
            return False, "seasonal_period_unavailable"
        if len(values) < seasonal_period:
            return False, "insufficient_seasonal_history"
    if model_name in {"ses", "holt", "holt_winters_additive", "holt_winters_multiplicative"}:
        if not continuous:
            return False, "history_not_continuous"
    if model_name == "ses" and valid_count < 3:
        return False, "insufficient_history"
    if model_name == "holt" and valid_count < 4:
        return False, "insufficient_history"
    if model_name.startswith("holt_winters"):
        if seasonal_period is None:
            return False, "seasonal_period_unavailable"
        if not seasonal_eligible or valid_count < seasonal_period * 2:
            return False, "insufficient_seasonal_history"
    if model_name == "holt_winters_multiplicative" and bool((values <= 0).any()):
        return False, "multiplicative_requires_positive_demand"
    if model_name == "moving_average":
        window = MOVING_AVERAGE_WINDOWS.get(frequency, 3)
        if valid_count < window:
            return False, "insufficient_moving_average_history"
    return True, None


def _safe_parameter(value: object) -> float | str | None:
    if value is None or isinstance(value, str):
        return value
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return round(number, 8) if math.isfinite(number) else None


def _statsmodels_parameters(fit: object, initialization: str) -> dict[str, object]:
    params = getattr(fit, "params", {})
    return {
        "alpha": _safe_parameter(params.get("smoothing_level")),
        "beta": _safe_parameter(params.get("smoothing_trend")),
        "gamma": _safe_parameter(params.get("smoothing_seasonal")),
        "damping": _safe_parameter(params.get("damping_trend")),
        "initial_level": _safe_parameter(params.get("initial_level")),
        "initial_trend": _safe_parameter(params.get("initial_trend")),
        "initialization_method": initialization,
        "optimized": True,
        "engine": "statsmodels",
        "parameter_source": "optimized",
    }


def _ses_fallback(values: np.ndarray, horizon: int) -> FittedForecast:
    best: tuple[float, float] | None = None
    for alpha in np.linspace(0.01, 0.99, 99):
        level = float(values[0])
        error = 0.0
        for actual in values[1:]:
            error += (float(actual) - level) ** 2
            level = float(alpha * actual + (1 - alpha) * level)
        if best is None or error < best[0]:
            best = (error, float(alpha))
    assert best is not None
    alpha = best[1]
    level = float(values[0])
    for actual in values[1:]:
        level = float(alpha * actual + (1 - alpha) * level)
    return FittedForecast(
        np.repeat(level, horizon),
        {
            "alpha": round(alpha, 8),
            "beta": None,
            "gamma": None,
            "initialization_method": "first_observation",
            "optimized": True,
            "optimization_method": "exhaustive_grid_search",
            "objective": "one_step_ahead_sse",
            "search_grid": "0.01..0.99 step 0.01",
            "engine": "numpy_fallback",
            "parameter_source": "optimized_grid_search",
        },
    )


def _holt_state(values: np.ndarray, alpha: float, beta: float) -> tuple[float, float, float]:
    level = float(values[0])
    trend = float(values[1] - values[0])
    error = 0.0
    for actual in values[1:]:
        predicted = level + trend
        error += (float(actual) - predicted) ** 2
        previous_level = level
        level = float(alpha * actual + (1 - alpha) * predicted)
        trend = float(beta * (level - previous_level) + (1 - beta) * trend)
    return error, level, trend


def _holt_fallback(values: np.ndarray, horizon: int) -> FittedForecast:
    best: tuple[float, float, float, float, float] | None = None
    grid = np.linspace(0.05, 0.95, 19)
    for alpha in grid:
        for beta in grid:
            error, level, trend = _holt_state(values, float(alpha), float(beta))
            if best is None or error < best[0]:
                best = (error, float(alpha), float(beta), level, trend)
    assert best is not None
    _, alpha, beta, level, trend = best
    return FittedForecast(
        np.asarray([level + (step + 1) * trend for step in range(horizon)]),
        {
            "alpha": round(alpha, 8),
            "beta": round(beta, 8),
            "gamma": None,
            "initialization_method": "first_two_observations",
            "optimized": True,
            "optimization_method": "exhaustive_grid_search",
            "objective": "one_step_ahead_sse",
            "search_grid": "0.05..0.95 step 0.05",
            "trend": "additive",
            "engine": "numpy_fallback",
            "parameter_source": "optimized_grid_search",
        },
    )


def _initial_seasonal(
    values: np.ndarray, period: int, seasonal: str
) -> tuple[float, float, np.ndarray]:
    first_mean = float(np.mean(values[:period]))
    second_mean = float(np.mean(values[period : period * 2]))
    trend = (second_mean - first_mean) / period
    if seasonal == "add":
        factors = values[:period] - first_mean
    else:
        factors = values[:period] / first_mean
    return first_mean, trend, np.asarray(factors, dtype=float)


def _holt_winters_state(
    values: np.ndarray,
    period: int,
    seasonal: str,
    alpha: float,
    beta: float,
    gamma: float,
) -> tuple[float, float, float, np.ndarray]:
    level, trend, factors = _initial_seasonal(values, period, seasonal)
    error = 0.0
    for index, actual in enumerate(values):
        factor_index = index % period
        factor = float(factors[factor_index])
        predicted = level + trend + factor if seasonal == "add" else (level + trend) * factor
        if index >= period:
            error += (float(actual) - predicted) ** 2
        previous_level = level
        if seasonal == "add":
            level = float(alpha * (actual - factor) + (1 - alpha) * (level + trend))
            trend = float(beta * (level - previous_level) + (1 - beta) * trend)
            factors[factor_index] = gamma * (actual - level) + (1 - gamma) * factor
        else:
            level = float(alpha * (actual / factor) + (1 - alpha) * (level + trend))
            trend = float(beta * (level - previous_level) + (1 - beta) * trend)
            factors[factor_index] = gamma * (actual / level) + (1 - gamma) * factor
    return error, level, trend, factors


def _holt_winters_fallback(
    values: np.ndarray, horizon: int, period: int, seasonal: str
) -> FittedForecast:
    best: tuple[float, float, float, float, float, float, np.ndarray] | None = None
    for alpha in NUMPY_HW_PARAMETER_GRID:
        for beta in NUMPY_HW_PARAMETER_GRID:
            for gamma in NUMPY_HW_PARAMETER_GRID:
                error, level, trend, factors = _holt_winters_state(
                    values, period, seasonal, alpha, beta, gamma
                )
                if best is None or error < best[0]:
                    best = (error, alpha, beta, gamma, level, trend, factors.copy())
    assert best is not None
    _, alpha, beta, gamma, level, trend, factors = best
    forecast = np.asarray(
        [
            level + step * trend + factors[(len(values) + step - 1) % period]
            if seasonal == "add"
            else (level + step * trend) * factors[(len(values) + step - 1) % period]
            for step in range(1, horizon + 1)
        ]
    )
    return FittedForecast(
        forecast,
        {
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
            "initialization_method": "heuristic_two_cycle",
            "optimized": True,
            "optimization_method": "exhaustive_grid_search",
            "objective": "one_step_ahead_sse_after_first_seasonal_cycle",
            "search_grid": "0.2,0.4,0.6,0.8",
            "search_candidates": len(NUMPY_HW_PARAMETER_GRID) ** 3,
            "trend": "additive",
            "seasonal": seasonal,
            "seasonal_period": period,
            "engine": "numpy_fallback",
            "parameter_source": "optimized_grid_search",
        },
    )


def fit_and_forecast(
    model_name: str,
    series: pd.Series,
    horizon: int,
    *,
    frequency: str,
    seasonal_period: int | None,
    seasonal_eligible: bool = True,
    continuous: bool | None = None,
) -> FittedForecast:
    """Fit one adapter to past values only and return exactly ``horizon`` predictions."""
    numeric = pd.to_numeric(series, errors="coerce").astype(float)
    is_continuous = bool(not numeric.isna().any()) if continuous is None else continuous
    eligible, reason = model_eligibility(
        model_name,
        numeric,
        frequency=frequency,
        seasonal_period=seasonal_period,
        seasonal_eligible=seasonal_eligible,
        continuous=is_continuous,
    )
    if not eligible:
        raise ModelNotEligible(reason or "model_not_eligible")
    valid = numeric.dropna().to_numpy(dtype=float)
    if model_name == "naive":
        return FittedForecast(
            np.repeat(valid[-1], horizon),
            {
                "strategy": "last_value",
                "engine": "native_baseline",
                "parameter_source": "deterministic_rule",
            },
        )
    if model_name == "seasonal_naive":
        assert seasonal_period is not None
        seasonal_values = numeric.iloc[-seasonal_period:].to_numpy(dtype=float)
        if not np.isfinite(seasonal_values).all():
            raise ModelNotEligible("latest_seasonal_cycle_contains_missing_values")
        values = np.resize(seasonal_values, horizon)
        return FittedForecast(
            values,
            {
                "seasonal_period": seasonal_period,
                "engine": "native_baseline",
                "parameter_source": "deterministic_rule",
            },
        )
    if model_name == "moving_average":
        window = MOVING_AVERAGE_WINDOWS.get(frequency, 3)
        mean = float(np.mean(valid[-window:]))
        return FittedForecast(
            np.repeat(mean, horizon),
            {
                "window": window,
                "engine": "native_baseline",
                "parameter_source": "configured_window",
            },
        )

    if SimpleExpSmoothing is None:
        if model_name == "ses":
            return _ses_fallback(valid, horizon)
        if model_name == "holt":
            return _holt_fallback(valid, horizon)
        assert seasonal_period is not None
        seasonal = "add" if model_name == "holt_winters_additive" else "mul"
        return _holt_winters_fallback(valid, horizon, seasonal_period, seasonal)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if model_name == "ses":
            assert SimpleExpSmoothing is not None
            fit = SimpleExpSmoothing(valid, initialization_method="estimated").fit(optimized=True)
            parameters = _statsmodels_parameters(fit, "estimated")
        elif model_name == "holt":
            assert Holt is not None
            fit = Holt(valid, damped_trend=False, initialization_method="estimated").fit(
                optimized=True
            )
            parameters = _statsmodels_parameters(fit, "estimated")
            parameters["trend"] = "additive"
        else:
            assert seasonal_period is not None
            assert ExponentialSmoothing is not None
            seasonal = "add" if model_name == "holt_winters_additive" else "mul"
            fit = ExponentialSmoothing(
                valid,
                trend="add",
                seasonal=seasonal,
                seasonal_periods=seasonal_period,
                initialization_method="estimated",
            ).fit(optimized=True)
            parameters = _statsmodels_parameters(fit, "estimated")
            parameters.update(
                {
                    "trend": "additive",
                    "seasonal": seasonal,
                    "seasonal_period": seasonal_period,
                }
            )
        forecast = np.asarray(fit.forecast(horizon), dtype=float)
    if len(forecast) != horizon or not np.isfinite(forecast).all():
        raise RuntimeError("model_generated_non_finite_forecast")
    return FittedForecast(forecast, parameters)
