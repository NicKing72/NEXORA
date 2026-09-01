"""Inventory coverage calculations with distinct physical and transit views."""

from __future__ import annotations


def coverage(inventory: float | None, average_demand: float) -> float | None:
    if inventory is None or average_demand <= 0:
        return None
    return inventory / average_demand


def coverage_views(
    on_hand: float | None, in_transit: float | None, average_demand: float
) -> tuple[float | None, float | None]:
    physical = coverage(on_hand, average_demand)
    combined = (
        coverage(on_hand + in_transit, average_demand)
        if on_hand is not None and in_transit is not None
        else None
    )
    return physical, combined
