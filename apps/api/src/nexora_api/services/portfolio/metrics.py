"""Deterministic forecast and inventory metrics for Portfolio Engine."""

from __future__ import annotations

from statistics import fmean, pstdev


def forecast_metrics(points: list[dict[str, object]]) -> dict[str, object]:
    values = [float(point["forecast"]) for point in points]
    total = sum(values)
    average = fmean(values)
    deviation = pstdev(values) if len(values) > 1 else 0.0
    variability = deviation / average if average > 0 else None

    def interval(level: str) -> dict[str, object]:
        lower_key = f"lower_{level}"
        upper_key = f"upper_{level}"
        pairs = [
            (float(point[lower_key]), float(point[upper_key]))
            for point in points
            if point.get(lower_key) is not None and point.get(upper_key) is not None
        ]
        return {
            "periods": len(pairs),
            "average_width": fmean(upper - lower for lower, upper in pairs) if pairs else None,
            "total_lower": sum(lower for lower, _ in pairs) if len(pairs) == len(points) else None,
            "total_upper": sum(upper for _, upper in pairs) if len(pairs) == len(points) else None,
        }

    return {
        "forecast_total": total,
        "forecast_average": average,
        "forecast_peak": max(values),
        "forecast_minimum": min(values),
        "forecast_variability": variability,
        "interval_information": {"80": interval("80"), "95": interval("95")},
    }


def inventory_coverage(
    current_inventory: float | None, forecast_average: float
) -> tuple[float | None, str]:
    if current_inventory is None:
        return None, "not_calculable_missing_inventory"
    if forecast_average <= 0:
        return None, "not_calculable_non_positive_forecast"
    return current_inventory / forecast_average, "calculated"


def projected_exposure(
    forecast_total: float,
    current_inventory: float | None,
    inbound_inventory: float | None,
) -> float | None:
    if current_inventory is None or inbound_inventory is None:
        return None
    return max(0.0, forecast_total - current_inventory - inbound_inventory)
