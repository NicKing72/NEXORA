"""Moving weighted-average valuation using Decimal arithmetic."""

from __future__ import annotations

from decimal import Decimal

from nexora_api.services.kardex.validation import ZERO, quantize


def weighted_average_in(
    quantity_before: Decimal,
    value_before: Decimal,
    quantity: Decimal,
    unit_cost: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    movement_total = quantize(quantity * unit_cost)
    quantity_after = quantize(quantity_before + quantity)
    value_after = quantize(value_before + movement_total)
    average = quantize(value_after / quantity_after) if quantity_after else ZERO
    return quantity_after, average, value_after, movement_total


def weighted_average_out(
    quantity_before: Decimal,
    _average_before: Decimal,
    value_before: Decimal,
    quantity: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    movement_total = quantize(value_before * quantity / quantity_before)
    quantity_after = quantize(quantity_before - quantity)
    value_after = ZERO if quantity_after == ZERO else quantize(value_before - movement_total)
    average_after = ZERO if quantity_after == ZERO else quantize(value_after / quantity_after)
    return quantity_after, average_after, value_after, movement_total
