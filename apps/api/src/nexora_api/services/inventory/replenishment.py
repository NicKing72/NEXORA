"""Net requirement and explicit constraint application."""

from __future__ import annotations

import math


def calculate_replenishment(
    *,
    forecast_total: float,
    on_hand: float | None,
    eligible_transit: float | None,
    safety_stock: float | None,
    committed: float | None,
    backorders: float | None,
    moq: float | None,
    lot_multiple: float | None,
    capacity: float | None,
) -> dict[str, object]:
    if on_hand is None or safety_stock is None:
        return {
            "raw_requirement": None,
            "recommended_quantity": None,
            "projected_inventory": None,
            "shortage": None,
            "surplus": None,
            "constraints": [],
            "warnings": ["manual_review_required_missing_inventory_or_safety_stock"],
        }
    transit = eligible_transit or 0.0
    committed_value = committed or 0.0
    backorder_value = backorders or 0.0
    projected = on_hand + transit - committed_value - backorder_value - forecast_total
    shortage, surplus = max(-projected, 0.0), max(projected, 0.0)
    raw = max(
        forecast_total + safety_stock + committed_value + backorder_value - on_hand - transit, 0.0
    )
    recommendation = raw
    constraints: list[dict[str, object]] = []
    if moq is not None and recommendation > 0 and recommendation < moq:
        constraints.append({"type": "moq", "before": recommendation, "after": moq})
        recommendation = moq
    if lot_multiple is not None and recommendation > 0 and lot_multiple > 0:
        rounded = math.ceil(recommendation / lot_multiple) * lot_multiple
        if rounded != recommendation:
            constraints.append({"type": "lot_multiple", "before": recommendation, "after": rounded})
            recommendation = rounded
    warnings: list[str] = []
    if capacity is not None and recommendation > capacity:
        constraints.append({"type": "capacity", "before": recommendation, "after": capacity})
        recommendation = capacity
        warnings.append("capacity_limits_recommendation_below_raw_requirement")
    return {
        "raw_requirement": raw,
        "recommended_quantity": recommendation,
        "projected_inventory": projected,
        "shortage": shortage,
        "surplus": surplus,
        "constraints": constraints,
        "warnings": warnings,
    }
