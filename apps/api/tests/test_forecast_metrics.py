"""Deterministic metric and ranking contracts for Forecast Core."""

from __future__ import annotations

import math

from nexora_api.services.forecasting.metrics import calculate_metrics, stability_from_folds
from nexora_api.services.forecasting.ranking import WMAPE_TIE_TOLERANCE, rank_models


def test_mae() -> None:
    assert calculate_metrics([1, 2, 3], [2, 2, 1])["mae"] == 1.0


def test_rmse() -> None:
    assert math.isclose(
        calculate_metrics([1, 2, 3], [2, 2, 1])["rmse"], math.sqrt(5 / 3), rel_tol=1e-6
    )


def test_smape_handles_both_values_zero() -> None:
    assert math.isclose(calculate_metrics([0, 2], [0, 4])["smape"], 1 / 3, rel_tol=1e-6)


def test_wmape() -> None:
    assert math.isclose(
        calculate_metrics([10, 20], [8, 25])["wmape"], 7 / 30, abs_tol=1e-6
    )


def test_bias_uses_forecast_minus_actual() -> None:
    metrics = calculate_metrics([10, 20], [12, 24])
    assert metrics["bias"] == 3.0
    assert metrics["bias_percent"] == 0.2


def test_mape_normal_case() -> None:
    assert calculate_metrics([10, 20], [8, 24])["mape"] == 0.2


def test_mape_is_null_when_any_actual_is_zero() -> None:
    assert calculate_metrics([0, 20], [1, 20])["mape"] is None


def test_wmape_is_null_when_denominator_is_zero() -> None:
    assert calculate_metrics([0, 0], [1, 2])["wmape"] is None


def _rankable(name: str, wmape: float, bias: float, stability: str = "high") -> dict:
    return {
        "model_name": name,
        "eligible": True,
        "status": "succeeded",
        "metrics": {"wmape": wmape, "bias_percent": bias, "rmse": wmape * 100},
        "stability": {"label": stability},
    }


def test_lowest_wmape_wins() -> None:
    ranked, reason = rank_models([_rankable("a", 0.20, 0.1), _rankable("b", 0.10, 0.1)])
    assert ranked[0]["model_name"] == "b"
    assert reason == "lowest_wmape"


def test_near_tie_of_point_three_percentage_points_uses_bias() -> None:
    ranked, reason = rank_models([_rankable("a", 0.100, 0.20), _rankable("b", 0.103, 0.01)])
    assert ranked[0]["model_name"] == "b"
    assert reason == "near_tie_bias_stability"


def test_clear_champion_reason_ignores_tie_between_later_challengers() -> None:
    ranked, reason = rank_models(
        [
            _rankable("holt_winters", 0.1322, -0.0543),
            _rankable("ses", 0.1464, -0.0337),
            _rankable("moving_average", 0.1472, -0.0421),
        ]
    )
    assert [item["model_name"] for item in ranked] == [
        "holt_winters",
        "ses",
        "moving_average",
    ]
    assert reason == "lowest_wmape"


def test_wmape_tolerance_uses_proportion_units_for_half_percentage_point() -> None:
    assert WMAPE_TIE_TOLERANCE == 0.005
    assert (0.1464 - 0.1322) > WMAPE_TIE_TOLERANCE
    assert (0.1352 - 0.1322) < WMAPE_TIE_TOLERANCE


def test_failed_and_noneligible_models_are_retained() -> None:
    failed = {
        "model_name": "failed",
        "eligible": True,
        "status": "failed",
        "metrics": {},
        "stability": {},
    }
    unavailable = {
        "model_name": "no",
        "eligible": False,
        "status": "not_eligible",
        "metrics": {},
        "stability": {},
    }
    ranked, _ = rank_models([_rankable("ok", 0.1, 0.0), failed, unavailable])
    assert [item["model_name"] for item in ranked] == ["ok", "failed", "no"]
    assert ranked[1]["rank"] is None


def test_fold_stability_classification() -> None:
    stability = stability_from_folds([{"wmape": 0.10}, {"wmape": 0.105}, {"wmape": 0.095}])
    assert stability["label"] == "high"
