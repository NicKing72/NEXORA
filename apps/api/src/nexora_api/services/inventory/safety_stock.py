"""Versioned service-level safety stock calculation."""

from __future__ import annotations

import math

Z_SCORES = {0.9: 1.2816, 0.95: 1.6449, 0.975: 1.96, 0.99: 2.3263}


def interval_sigma(points: list[dict[str, object]]) -> float | None:
    estimates = []
    for point in points:
        lower, upper = point.get("lower_95"), point.get("upper_95")
        if isinstance(lower, (int, float)) and isinstance(upper, (int, float)) and upper >= lower:
            estimates.append((float(upper) - float(lower)) / (2 * 1.96))
    return sum(estimates) / len(estimates) if estimates else None


def calculate_safety_stock(
    *, service_level: float | None, sigma_period: float | None, lead_time_periods: float | None
) -> tuple[float | None, dict[str, object]]:
    if service_level is None or sigma_period is None or lead_time_periods is None:
        return None, {
            "status": "not_calculable",
            "reason": "missing_service_level_dispersion_or_lead_time",
        }
    z = Z_SCORES.get(round(service_level, 3))
    if z is None:
        return None, {"status": "not_calculable", "reason": "unsupported_service_level"}
    sigma_lt = sigma_period * math.sqrt(lead_time_periods)
    result = z * sigma_lt
    return result, {
        "status": "calculated",
        "formula": "SS = z × σ_period × √lead_time",
        "substitution": f"{z:.4f} × {sigma_period:.6f} × √{lead_time_periods:g}",
        "z_score": z,
        "sigma_period": sigma_period,
        "sigma_lead_time": sigma_lt,
        "result": result,
        "unit": "units",
    }
