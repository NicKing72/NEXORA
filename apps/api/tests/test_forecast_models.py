"""Forecast adapter tests without future-data access."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import nexora_api.services.forecasting.models as forecast_models
from nexora_api.services.forecasting.models import ModelNotEligible, fit_and_forecast
from nexora_api.services.forecasting.service import future_index


def _series(values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.date_range("2025-01-01", periods=len(values), freq="D"))


def test_naive_uses_last_value() -> None:
    result = fit_and_forecast(
        "naive", _series([1, 2, 4]), 3, frequency="daily", seasonal_period=None
    )
    assert result.values.tolist() == [4, 4, 4]


def test_seasonal_naive_repeats_last_cycle() -> None:
    result = fit_and_forecast(
        "seasonal_naive", _series([1, 2, 3, 4, 5, 6]), 5, frequency="daily", seasonal_period=3
    )
    assert result.values.tolist() == [4, 5, 6, 4, 5]


def test_moving_average_uses_frequency_window() -> None:
    result = fit_and_forecast(
        "moving_average", _series(list(range(1, 9))), 2, frequency="daily", seasonal_period=None
    )
    assert result.values.tolist() == [5.0, 5.0]
    assert result.parameters["window"] == 7


def test_ses_returns_estimated_alpha() -> None:
    result = fit_and_forecast(
        "ses", _series([10, 11, 9, 12, 11, 13]), 2, frequency="daily", seasonal_period=None
    )
    assert len(result.values) == 2
    assert result.parameters["alpha"] is not None


def test_holt_returns_alpha_and_beta() -> None:
    result = fit_and_forecast(
        "holt", _series([10, 12, 14, 16, 18, 20]), 2, frequency="daily", seasonal_period=None
    )
    assert result.values[1] > result.values[0]
    assert result.parameters["alpha"] is not None
    assert result.parameters["beta"] is not None


def test_holt_winters_additive() -> None:
    values = [10 + (index % 7) * 2 + index * 0.1 for index in range(35)]
    result = fit_and_forecast(
        "holt_winters_additive", _series(values), 7, frequency="daily", seasonal_period=7
    )
    assert len(result.values) == 7
    assert result.parameters["gamma"] is not None
    assert result.parameters["seasonal_period"] == 7


def test_numpy_holt_winters_parameters_are_grid_optimized_not_fixed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(forecast_models, "SimpleExpSmoothing", None)
    smooth = _series([20 + 0.5 * index + (index % 7) * 2 for index in range(42)])
    accelerating = _series([30 + 0.08 * index**2 + (index % 7) * 4 for index in range(42)])

    smooth_result = fit_and_forecast(
        "holt_winters_additive", smooth, 7, frequency="daily", seasonal_period=7
    )
    accelerating_result = fit_and_forecast(
        "holt_winters_additive", accelerating, 7, frequency="daily", seasonal_period=7
    )

    assert smooth_result.parameters["engine"] == "numpy_fallback"
    assert smooth_result.parameters["parameter_source"] == "optimized_grid_search"
    assert smooth_result.parameters["initialization_method"] == "heuristic_two_cycle"
    assert smooth_result.parameters["search_candidates"] == 64
    assert (
        smooth_result.parameters["alpha"],
        smooth_result.parameters["beta"],
        smooth_result.parameters["gamma"],
    ) == (0.2, 0.2, 0.8)
    assert (
        accelerating_result.parameters["alpha"],
        accelerating_result.parameters["beta"],
        accelerating_result.parameters["gamma"],
    ) == (0.8, 0.4, 0.8)


def test_holt_winters_multiplicative_positive_data() -> None:
    values = [20 + (index % 7) * 3 for index in range(35)]
    result = fit_and_forecast(
        "holt_winters_multiplicative", _series(values), 7, frequency="daily", seasonal_period=7
    )
    assert len(result.values) == 7
    assert np.isfinite(result.values).all()


def test_holt_winters_multiplicative_rejects_zero() -> None:
    values = [20 + (index % 7) for index in range(35)]
    values[10] = 0
    with pytest.raises(ModelNotEligible, match="multiplicative_requires_positive_demand"):
        fit_and_forecast(
            "holt_winters_multiplicative", _series(values), 7, frequency="daily", seasonal_period=7
        )


def test_insufficient_seasonal_history_is_rejected() -> None:
    with pytest.raises(ModelNotEligible, match="insufficient_seasonal_history"):
        fit_and_forecast(
            "holt_winters_additive", _series([1] * 13), 2, frequency="daily", seasonal_period=7
        )


def test_future_daily_dates_start_after_cutoff() -> None:
    index = future_index(pd.Timestamp("2025-12-31"), "daily", 2)
    assert [value.strftime("%Y-%m-%d") for value in index] == ["2026-01-01", "2026-01-02"]


def test_future_weekly_dates_remain_mondays() -> None:
    index = future_index(pd.Timestamp("2025-12-29"), "weekly", 2)
    assert [value.strftime("%Y-%m-%d") for value in index] == ["2026-01-05", "2026-01-12"]


def test_future_monthly_dates_use_calendar_starts() -> None:
    index = future_index(pd.Timestamp("2025-12-01"), "monthly", 2)
    assert [value.strftime("%Y-%m-%d") for value in index] == ["2026-01-01", "2026-02-01"]
