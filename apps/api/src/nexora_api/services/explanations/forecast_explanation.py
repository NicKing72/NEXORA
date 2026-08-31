"""Descriptive summary of persisted forecast points and empirical intervals."""

from __future__ import annotations

from statistics import fmean

from nexora_api.models.dataset import ForecastRun

TREND_THRESHOLD = 0.03
TREND_RULE_VERSION = "forecast_output_trend_v1"


def _trend(values: list[float]) -> dict[str, object]:
    if len(values) < 2:
        return {"label": "stable", "relative_change": None, "rule": TREND_RULE_VERSION}
    first, last = values[0], values[-1]
    if abs(first) < 1e-12:
        label = "stable" if abs(last) < 1e-12 else "mixed"
        change = None
    else:
        change = (last - first) / abs(first)
        label = "stable" if abs(change) < TREND_THRESHOLD else (
            "increasing" if change > 0 else "decreasing"
        )
    return {
        "label": label,
        "relative_change": None if change is None else round(change, 6),
        "rule": TREND_RULE_VERSION,
        "threshold": TREND_THRESHOLD,
    }


def forecast_snapshot(run: ForecastRun) -> dict[str, object]:
    points = sorted(run.points, key=lambda item: item.timestamp)
    values = [float(item.forecast) for item in points]
    serialized = [
        {
            "timestamp": item.timestamp.date().isoformat(),
            "forecast": item.forecast,
            "lower_80": item.lower_80,
            "upper_80": item.upper_80,
            "width_80": None
            if item.lower_80 is None or item.upper_80 is None
            else round(item.upper_80 - item.lower_80, 6),
            "lower_95": item.lower_95,
            "upper_95": item.upper_95,
            "width_95": None
            if item.lower_95 is None or item.upper_95 is None
            else round(item.upper_95 - item.lower_95, 6),
        }
        for item in points
    ]
    widths_80 = [float(item["width_80"]) for item in serialized if item["width_80"] is not None]
    widths_95 = [float(item["width_95"]) for item in serialized if item["width_95"] is not None]
    return {
        "summary": {
            "start": serialized[0]["timestamp"] if serialized else None,
            "end": serialized[-1]["timestamp"] if serialized else None,
            "frequency": run.frequency,
            "horizon": run.requested_horizon,
            "period_count": len(serialized),
            "total": round(sum(values), 6) if values else None,
            "average": round(fmean(values), 6) if values else None,
            "minimum": round(min(values), 6) if values else None,
            "maximum": round(max(values), 6) if values else None,
            "trend": _trend(values),
            "interval_method": (run.preprocessing_summary or {}).get("interval_method"),
            "interval_residual_count": (run.preprocessing_summary or {}).get(
                "interval_residual_count"
            ),
            "has_80_interval": bool(widths_80),
            "has_95_interval": bool(widths_95),
            "average_width_80": round(fmean(widths_80), 6) if widths_80 else None,
            "average_width_95": round(fmean(widths_95), 6) if widths_95 else None,
        },
        "points": serialized,
    }
