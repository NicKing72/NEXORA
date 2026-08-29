"""Preparation and rolling-origin invariants."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta

import pandas as pd

from nexora_api.services.forecasting.backtesting import (
    assess_model_backtest_evaluability,
    build_fold_windows,
    evaluate_models,
)
from nexora_api.services.forecasting.models import model_eligibility
from nexora_api.services.forecasting.preprocessing import prepare_training_series


def _profile(demands: list[float | None], partials: set[int] | None = None) -> dict:
    partials = partials or set()
    return {
        "points": [
            {
                "date": (date(2025, 1, 1) + timedelta(days=index)).isoformat(),
                "demand": demand,
                "is_partial": index in partials,
            }
            for index, demand in enumerate(demands)
        ],
        "statistics": {
            "underlying_quality": {
                "outlier_observations": 2,
                "possible_stockout_observations": 1,
            }
        },
    }


def test_partial_periods_are_excluded() -> None:
    prepared = prepare_training_series(_profile([1, 2, 3], {2}))
    assert prepared.series.tolist() == [1, 2]
    assert prepared.excluded_partial_dates == ["2025-01-03"]


def test_original_profile_is_not_modified() -> None:
    profile = _profile([1, None, 3])
    before = deepcopy(profile)
    prepare_training_series(profile)
    assert profile == before


def test_small_internal_missing_gap_is_interpolated() -> None:
    values: list[float | None] = list(range(1, 22))
    values[10] = None
    prepared = prepare_training_series(_profile(values))
    assert prepared.series.iloc[10] == 11
    assert prepared.continuous is True


def test_large_gap_blocks_continuous_models() -> None:
    values: list[float | None] = list(range(1, 31))
    values[10:13] = [None, None, None]
    prepared = prepare_training_series(_profile(values))
    assert prepared.continuous is False
    assert prepared.summary["maximum_consecutive_gap"] == 3


def test_interpolation_audit_is_generated() -> None:
    values: list[float | None] = list(range(1, 22))
    values[10] = None
    audit = prepare_training_series(_profile(values)).interpolation_audit
    assert audit == [
        {
            "timestamp": "2025-01-11",
            "original_value": None,
            "transformed_value": 11.0,
            "method": "linear_time_interpolation",
            "reason": "internal_gap_within_safe_threshold",
        }
    ]


def test_outliers_and_stockouts_are_preserved_as_warnings() -> None:
    prepared = prepare_training_series(_profile([1, 100, 0, 3]))
    assert prepared.series.tolist() == [1, 100, 0, 3]
    assert prepared.summary["outliers_preserved"] == 2
    assert prepared.summary["possible_stockouts_preserved"] == 1


def test_zero_values_are_preserved() -> None:
    prepared = prepare_training_series(_profile([1, 0, 3]))
    assert prepared.series.iloc[1] == 0
    assert prepared.summary["zero_values_preserved"] == 1


def test_folds_respect_temporal_order_and_expand() -> None:
    folds = build_fold_windows(50, 5)
    assert len(folds) == 5
    assert all(fold.train_end < fold.validation_end for fold in folds)
    assert [fold.train_end for fold in folds] == sorted(fold.train_end for fold in folds)
    assert all(
        left.validation_end == right.train_end
        for left, right in zip(folds, folds[1:], strict=False)
    )


def test_insufficient_history_has_no_folds() -> None:
    assert build_fold_windows(9, 6) == []


def test_model_can_be_final_fit_eligible_but_not_backtest_evaluable() -> None:
    series = pd.Series(
        [91.0] * 104,
        index=pd.date_range("2024-01-01", periods=104, freq="W-MON"),
    )
    final_eligible, _ = model_eligibility(
        "holt_winters_additive",
        series,
        frequency="weekly",
        seasonal_period=52,
        seasonal_eligible=True,
        continuous=True,
    )
    backtest = assess_model_backtest_evaluability(
        "holt_winters_additive",
        series,
        frequency="weekly",
        requested_horizon=12,
        seasonal_period=52,
        seasonal_eligible=True,
    )
    assert final_eligible is True
    assert backtest == {
        "evaluable": False,
        "reason": "insufficient_fold_seasonal_history",
        "evaluable_folds": 0,
        "total_folds": 5,
    }


def test_model_can_be_final_fit_eligible_and_backtest_evaluable() -> None:
    series = pd.Series(
        [91.0] * 140,
        index=pd.date_range("2023-05-01", periods=140, freq="W-MON"),
    )
    backtest = assess_model_backtest_evaluability(
        "holt_winters_additive",
        series,
        frequency="weekly",
        requested_horizon=12,
        seasonal_period=52,
        seasonal_eligible=True,
    )
    assert backtest["evaluable"] is True
    assert backtest["evaluable_folds"] == 4
    assert backtest["total_folds"] == 5


def test_nonpositive_series_is_not_final_fit_eligible_for_multiplicative_model() -> None:
    series = pd.Series([10.0] * 103 + [0.0])
    eligible, reason = model_eligibility(
        "holt_winters_multiplicative",
        series,
        frequency="weekly",
        seasonal_period=52,
        seasonal_eligible=True,
        continuous=True,
    )
    assert eligible is False
    assert reason == "multiplicative_requires_positive_demand"


def test_global_metrics_use_all_out_of_sample_errors() -> None:
    prepared = prepare_training_series(_profile([float(index) for index in range(1, 51)]))
    results, _ = evaluate_models(
        prepared.series,
        frequency="daily",
        requested_horizon=5,
        seasonal_period=7,
        seasonal_eligible=True,
        continuous=True,
    )
    naive = next(item for item in results if item["model_name"] == "naive")
    fold_observations = sum(fold["metrics"]["observations"] for fold in naive["folds"])
    assert naive["metrics"]["observations"] == fold_observations
