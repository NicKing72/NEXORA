"""Persistent FIFO layer consumption and allocation evidence."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from nexora_api.models.kardex import KardexAllocation, KardexMovement
from nexora_api.services.kardex.validation import INBOUND_TYPES, ZERO, quantize


def available_layers(db: Session, product_id: str) -> list[dict[str, object]]:
    movements = (
        db.query(KardexMovement)
        .filter(
            KardexMovement.product_id == product_id,
            KardexMovement.movement_type.in_(INBOUND_TYPES),
        )
        .order_by(KardexMovement.timestamp, KardexMovement.created_at, KardexMovement.id)
        .all()
    )
    consumed_rows = (
        db.query(
            KardexAllocation.inbound_movement_id,
            func.coalesce(func.sum(KardexAllocation.quantity), 0),
        )
        .join(
            KardexMovement,
            KardexMovement.id == KardexAllocation.inbound_movement_id,
        )
        .filter(KardexMovement.product_id == product_id)
        .group_by(KardexAllocation.inbound_movement_id)
        .all()
    )
    consumed = {movement_id: quantize(quantity) for movement_id, quantity in consumed_rows}
    return [
        {
            "movement_id": movement.id,
            "quantity": remaining,
            "unit_cost": quantize(movement.unit_cost),
        }
        for movement in movements
        if (remaining := quantize(movement.quantity - consumed.get(movement.id, ZERO))) > ZERO
    ]


def consume_fifo(
    db: Session, product_id: str, quantity: Decimal
) -> tuple[list[dict[str, Decimal | str]], Decimal]:
    remaining = quantize(quantity)
    allocations: list[dict[str, Decimal | str]] = []
    total = ZERO
    for layer in available_layers(db, product_id):
        if remaining <= ZERO:
            break
        layer_quantity = Decimal(layer["quantity"])
        consumed = min(layer_quantity, remaining)
        unit_cost = Decimal(layer["unit_cost"])
        allocation_total = quantize(consumed * unit_cost)
        allocations.append(
            {
                "inbound_movement_id": str(layer["movement_id"]),
                "quantity": quantize(consumed),
                "unit_cost": unit_cost,
                "total_cost": allocation_total,
            }
        )
        total = quantize(total + allocation_total)
        remaining = quantize(remaining - consumed)
    return allocations, total
