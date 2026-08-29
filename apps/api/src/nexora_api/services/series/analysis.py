"""Explainable descriptive analysis for an already constructed demand series."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

SEASONAL_CANDIDATES: dict[str, tuple[int, str]] = {
    "daily": (7, "weekly"),
    "weekly": (52, "annual"),
    "monthly": (12, "annual"),
    "quarterly": (4, "annual"),
}


def _finite(value: float | int | None, digits: int = 6) -> float | None:
    if value is None or not math.isfinite(float(value)):
        return None
    return round(float(value), digits)


def series_statistics(
    series: pd.Series, partial_mask: pd.Series
) -> dict[str, object]:
    """Describe the visible series while excluding partial periods from distribution metrics."""
    numeric = pd.to_numeric(series, errors="coerce")
    partial = partial_mask.reindex(numeric.index, fill_value=False).astype(bool)
    visible_valid = numeric.dropna()
    analyzed = numeric[~partial].dropna()
    mean = float(analyzed.mean()) if not analyzed.empty else None
    deviation = float(analyzed.std(ddof=0)) if not analyzed.empty else None
    coefficient = None
    if mean is not None and deviation is not None and abs(mean) > 1e-12:
        coefficient = deviation / mean
    return {
        "periods": int(len(numeric)),
        "valid_periods": int(visible_valid.count()),
        "complete_periods": int((~partial).sum()),
        "partial_periods": int(partial.sum()),
        "analyzed_periods": int(analyzed.count()),
        "first_date": None,
        "last_date": None,
        "total_demand": _finite(float(visible_valid.sum())) if not visible_valid.empty else None,
        "mean_demand": _finite(mean),
        "median_demand": _finite(float(analyzed.median())) if not analyzed.empty else None,
        "minimum_demand": _finite(float(analyzed.min())) if not analyzed.empty else None,
        "maximum_demand": _finite(float(analyzed.max())) if not analyzed.empty else None,
        "standard_deviation": _finite(deviation),
        "coefficient_of_variation": _finite(coefficient),
        "completely_missing_periods": int(numeric.isna().sum()),
        "zero_demand_periods": int((visible_valid == 0).sum()),
        "analysis_excludes_partial_periods": True,
        "total_includes_partial_periods": True,
    }


def underlying_quality_statistics(
    *,
    source_observations: int,
    event_totals: dict[str, int],
    affected_periods: dict[str, int],
) -> dict[str, object]:
    """Keep source-row audit counts separate from resulting-period statistics."""
    return {
        "source_observations": source_observations,
        "missing_demand_values": int(event_totals.get("missing", 0)),
        "zero_demand_observations": int(event_totals.get("zero", 0)),
        "outlier_observations": int(event_totals.get("outlier", 0)),
        "possible_stockout_observations": int(event_totals.get("stockout", 0)),
        "affected_periods": affected_periods,
    }


def _trend_classification(change: float | None) -> str:
    if change is None or abs(change) < 3:
        return "stable"
    direction = "increasing" if change > 0 else "decreasing"
    magnitude = abs(change)
    if magnitude < 10:
        strength = "slight"
    elif magnitude < 25:
        strength = "moderate"
    else:
        strength = "strong"
    return f"{direction}_{strength}"


def pattern_summary(series: pd.Series, excluded_partial_periods: int = 0) -> dict[str, object]:
    numeric = pd.to_numeric(series, errors="coerce")
    valid_mask = numeric.notna()
    valid = numeric[valid_mask]
    if len(valid) < 2:
        return {
            "trend": "stable",
            "slope_per_period": 0.0,
            "approximate_change_percent": None,
            "volatility": "low",
            "stability": "insufficient",
            "intermittent": False,
            "zero_percentage": 0.0,
            "adi": None,
            "analyzed_periods": int(len(valid)),
            "excluded_partial_periods": excluded_partial_periods,
            "signals": ["insufficient_history"],
        }

    positions = np.flatnonzero(valid_mask.to_numpy())
    values = valid.to_numpy(dtype=float)
    slope = float(np.polyfit(positions, values, 1)[0])
    mean = float(valid.mean())
    approximate_change = None
    if abs(mean) > 1e-12:
        approximate_change = slope * max(len(numeric) - 1, 1) / abs(mean) * 100
    trend = _trend_classification(approximate_change)

    deviation = float(valid.std(ddof=0))
    cv = abs(deviation / mean) if abs(mean) > 1e-12 else math.inf
    volatility = "high" if cv >= 0.5 else "moderate" if cv >= 0.25 else "low"
    zero_percentage = float((valid == 0).mean() * 100)
    positive_count = int((valid > 0).sum())
    adi = float(len(valid) / positive_count) if positive_count else None
    intermittent = bool(adi is not None and adi > 1.32)
    stability = (
        "stable"
        if volatility == "low" and trend == "stable" and zero_percentage < 10
        else "variable"
    )
    signals = [f"trend_{trend}", f"volatility_{volatility}"]
    if intermittent:
        signals.append("intermittent_demand")
    if stability == "stable":
        signals.append("stable_history")
    if excluded_partial_periods:
        signals.append("partial_periods_excluded")
    return {
        "trend": trend,
        "slope_per_period": _finite(slope) or 0.0,
        "approximate_change_percent": _finite(approximate_change, 2),
        "volatility": volatility,
        "stability": stability,
        "intermittent": intermittent,
        "zero_percentage": _finite(zero_percentage, 2) or 0.0,
        "adi": _finite(adi, 3),
        "analyzed_periods": int(len(valid)),
        "excluded_partial_periods": excluded_partial_periods,
        "signals": signals,
    }


def seasonality_advice(
    series: pd.Series, frequency: str, excluded_partial_periods: int = 0
) -> dict[str, object]:
    candidate = SEASONAL_CANDIDATES.get(frequency)
    if candidate is None:
        return {
            "candidate_label": None,
            "candidate_period": None,
            "evidence": "insufficient",
            "autocorrelation": None,
            "paired_observations": 0,
            "complete_cycles": 0,
            "analyzed_periods": int(pd.to_numeric(series, errors="coerce").notna().sum()),
            "excluded_partial_periods": excluded_partial_periods,
            "conclusion": "insufficient",
        }

    period, label = candidate
    numeric = pd.to_numeric(series, errors="coerce")
    valid_count = int(numeric.notna().sum())
    cycles = valid_count // period
    if len(numeric) <= period:
        return {
            "candidate_label": label,
            "candidate_period": period,
            "evidence": "insufficient",
            "autocorrelation": None,
            "paired_observations": 0,
            "complete_cycles": cycles,
            "analyzed_periods": valid_count,
            "excluded_partial_periods": excluded_partial_periods,
            "conclusion": "insufficient",
        }

    left = numeric.iloc[:-period].reset_index(drop=True)
    right = numeric.iloc[period:].reset_index(drop=True)
    paired = pd.DataFrame({"left": left, "right": right}).dropna()
    autocorrelation = None
    if len(paired) >= max(8, period) and paired["left"].std() > 0 and paired["right"].std() > 0:
        autocorrelation = float(paired["left"].corr(paired["right"]))

    if autocorrelation is None:
        evidence = "insufficient"
        conclusion = "insufficient"
    elif autocorrelation >= 0.6:
        evidence = "high"
        conclusion = "potential"
    elif autocorrelation >= 0.35:
        evidence = "moderate"
        conclusion = "potential"
    else:
        evidence = "low"
        conclusion = "inconclusive"
    return {
        "candidate_label": label,
        "candidate_period": period,
        "evidence": evidence,
        "autocorrelation": _finite(autocorrelation, 4),
        "paired_observations": int(len(paired)),
        "complete_cycles": cycles,
        "analyzed_periods": valid_count,
        "excluded_partial_periods": excluded_partial_periods,
        "conclusion": conclusion,
    }


def holt_winters_eligibility(
    series: pd.Series,
    seasonality: dict[str, object],
    *,
    total_periods: int,
    excluded_partial_periods: int = 0,
) -> dict[str, object]:
    period = seasonality.get("candidate_period")
    numeric = pd.to_numeric(series, errors="coerce")
    eligible_periods = int(len(numeric))
    missing = int(numeric.isna().sum())
    evidence = str(seasonality.get("evidence", "insufficient"))
    if not isinstance(period, int):
        return {
            "compatible": False,
            "candidate_period": None,
            "total_periods": total_periods,
            "eligible_periods": eligible_periods,
            "required_observations": None,
            "complete_cycles": 0,
            "missing_values": missing,
            "excluded_partial_periods": excluded_partial_periods,
            "seasonal_evidence": evidence,
            "recommendation": "not_available",
            "reason_code": "unsupported_frequency",
        }
    required = period * 2
    cycles = eligible_periods // period
    compatible = eligible_periods >= required
    if not compatible:
        recommendation = "not_available"
    elif evidence == "high" and cycles >= 3:
        recommendation = "favorable"
    else:
        recommendation = "limited"
    return {
        "compatible": compatible,
        "candidate_period": period,
        "total_periods": total_periods,
        "eligible_periods": eligible_periods,
        "required_observations": required,
        "complete_cycles": cycles,
        "missing_values": missing,
        "excluded_partial_periods": excluded_partial_periods,
        "seasonal_evidence": evidence,
        "recommendation": recommendation,
        "reason_code": "sufficient_history" if compatible else "insufficient_history",
    }
