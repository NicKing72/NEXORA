"""Lead-time demand and reorder point calculations."""

from __future__ import annotations

import math

TIME_UNIT_BY_FREQUENCY = {"daily": "days", "weekly": "weeks", "monthly": "months"}


def compatible_lead_time(frequency: str, lead_time: float | None, unit: str | None) -> float | None:
    if lead_time is None or unit != TIME_UNIT_BY_FREQUENCY.get(frequency):
        return None
    return lead_time


def demand_during_lead_time(values: list[float], periods: float | None) -> float | None:
    if periods is None or periods < 0 or periods > len(values):
        return None
    whole = int(math.floor(periods))
    fraction = periods - whole
    result = sum(values[:whole])
    if fraction and whole < len(values):
        result += values[whole] * fraction
    return result


def reorder_point(lead_time_demand: float | None, safety_stock: float | None) -> float | None:
    if lead_time_demand is None or safety_stock is None:
        return None
    return lead_time_demand + safety_stock
