"""Explicit classical EOQ calculation."""

from __future__ import annotations

import math

PERIODS_PER_YEAR = {"daily": 365, "weekly": 52, "monthly": 12}


def calculate_eoq(
    *,
    average_demand: float,
    frequency: str,
    order_cost: float | None,
    holding_cost: float | None,
    holding_rate: float | None,
    unit_cost: float | None,
) -> tuple[float | None, dict[str, object], float | None]:
    factor = PERIODS_PER_YEAR.get(frequency)
    annual_holding = holding_cost
    source = "declared_per_unit_year" if holding_cost is not None else None
    if annual_holding is None and holding_rate is not None and unit_cost is not None:
        annual_holding = holding_rate * unit_cost
        source = "holding_rate_times_unit_cost"
    if factor is None or order_cost is None or annual_holding is None or annual_holding <= 0:
        return (
            None,
            {"status": "not_calculable", "reason": "missing_or_incompatible_economic_inputs"},
            annual_holding,
        )
    annual_demand = average_demand * factor
    result = math.sqrt((2 * annual_demand * order_cost) / annual_holding)
    return (
        result,
        {
            "status": "calculated",
            "formula": "EOQ = √((2 × D × S) / H)",
            "substitution": (
                f"√((2 × {annual_demand:.6f} × {order_cost:.6f}) / {annual_holding:.6f})"
            ),
            "annual_demand": annual_demand,
            "annualization_factor": factor,
            "holding_cost_source": source,
            "result": result,
            "unit": "units",
        },
        annual_holding,
    )
