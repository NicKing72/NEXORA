"""Explicit, non-mutating preparation of a Series Engine profile for training."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PreparedSeries:
    series: pd.Series
    original_series: pd.Series
    excluded_partial_dates: list[str]
    interpolation_audit: list[dict[str, object]]
    continuous: bool
    summary: dict[str, object]
    warnings: list[str]


def _maximum_gap(mask: pd.Series) -> int:
    maximum = current = 0
    for missing in mask.astype(bool):
        current = current + 1 if missing else 0
        maximum = max(maximum, current)
    return maximum


def prepare_training_series(profile: dict[str, object]) -> PreparedSeries:
    """Exclude partial periods and conservatively interpolate only small internal gaps."""
    points = list(profile["points"])  # type: ignore[arg-type]
    frame = pd.DataFrame(points).copy(deep=True)
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame = frame.set_index("date").sort_index()
    original = pd.to_numeric(frame["demand"], errors="coerce").astype(float)
    partial_mask = frame["is_partial"].astype(bool)
    excluded_dates = [index.strftime("%Y-%m-%d") for index in frame.index[partial_mask]]
    eligible = original.loc[~partial_mask].copy(deep=True)
    missing_mask = eligible.isna()
    missing_count = int(missing_mask.sum())
    missing_ratio = missing_count / len(eligible) if len(eligible) else 0.0
    edge_missing = bool(missing_count and (missing_mask.iloc[0] or missing_mask.iloc[-1]))
    maximum_gap = _maximum_gap(missing_mask)
    can_interpolate = bool(
        missing_count
        and not edge_missing
        and maximum_gap <= 2
        and missing_ratio <= 0.05
    )
    audit: list[dict[str, object]] = []
    prepared = eligible.copy(deep=True)
    if can_interpolate:
        interpolated = prepared.interpolate(method="time", limit_area="inside")
        for timestamp in prepared.index[missing_mask]:
            transformed = interpolated.loc[timestamp]
            audit.append(
                {
                    "timestamp": timestamp.strftime("%Y-%m-%d"),
                    "original_value": None,
                    "transformed_value": round(float(transformed), 6),
                    "method": "linear_time_interpolation",
                    "reason": "internal_gap_within_safe_threshold",
                }
            )
        prepared = interpolated
    continuous = bool(not prepared.isna().any())
    valid_training = prepared.dropna()
    training_cutoff = (
        valid_training.index.max().strftime("%Y-%m-%d") if not valid_training.empty else None
    )
    quality = profile["statistics"]["underlying_quality"]  # type: ignore[index]
    warnings: list[str] = []
    if excluded_dates:
        warnings.append("partial_periods_excluded")
    if audit:
        warnings.append("small_internal_gaps_interpolated")
    if missing_count and not continuous:
        warnings.append("history_not_continuous")
    if int(quality["outlier_observations"]):
        warnings.append("outliers_preserved")
    if int(quality["possible_stockout_observations"]):
        warnings.append("possible_stockouts_preserved")
    summary = {
        "source_periods": int(len(original)),
        "training_periods": int(len(prepared)),
        "valid_training_values": int(prepared.notna().sum()),
        "excluded_partial_periods": len(excluded_dates),
        "excluded_partial_dates": excluded_dates,
        "missing_before": missing_count,
        "missing_ratio": round(missing_ratio, 6),
        "maximum_consecutive_gap": maximum_gap,
        "edge_missing": edge_missing,
        "interpolated_values": len(audit),
        "interpolation_method": "linear_time_interpolation" if audit else None,
        "continuous_for_training": continuous,
        "training_cutoff": training_cutoff,
        "outliers_preserved": int(quality["outlier_observations"]),
        "possible_stockouts_preserved": int(quality["possible_stockout_observations"]),
        "zero_values_preserved": int((prepared == 0).sum()),
    }
    return PreparedSeries(
        series=prepared,
        original_series=original.copy(deep=True),
        excluded_partial_dates=excluded_dates,
        interpolation_audit=audit,
        continuous=continuous,
        summary=summary,
        warnings=warnings,
    )


def finite_values(series: pd.Series) -> np.ndarray:
    return series[np.isfinite(series)].to_numpy(dtype=float)
