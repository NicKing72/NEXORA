"""Balance reconstruction helpers; no independent editable stock is stored."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from nexora_api.models.kardex import InventoryProduct, KardexMovement
from nexora_api.services.kardex.validation import ZERO, quantize


def latest_movement(
    db: Session, product_id: str, *, cutoff: datetime | None = None
) -> KardexMovement | None:
    query = db.query(KardexMovement).filter(KardexMovement.product_id == product_id)
    if cutoff is not None:
        query = query.filter(
            KardexMovement.timestamp <= cutoff,
            KardexMovement.created_at <= cutoff,
        )
    return query.order_by(
        KardexMovement.timestamp.desc(),
        KardexMovement.created_at.desc(),
        KardexMovement.id.desc(),
    ).first()


def current_values(
    db: Session, product_id: str, *, cutoff: datetime | None = None
) -> tuple[Decimal | None, Decimal | None, Decimal | None, KardexMovement | None]:
    movement = latest_movement(db, product_id, cutoff=cutoff)
    if movement is None:
        return None, None, None, None
    return (
        quantize(movement.balance_quantity),
        quantize(movement.balance_unit_cost),
        quantize(movement.balance_total),
        movement,
    )


def empty_balance() -> tuple[Decimal, Decimal, Decimal]:
    return ZERO, ZERO, ZERO


def product_balance(
    db: Session, product: InventoryProduct, cutoff: datetime | None = None
) -> dict[str, object]:
    quantity, unit_cost, total, movement = current_values(db, product.id, cutoff=cutoff)
    return {
        "product_id": product.id,
        "sku": product.sku,
        "as_of": movement.timestamp if movement else None,
        "movement_id": movement.id if movement else None,
        "quantity": quantity,
        "unit_cost": unit_cost,
        "total_value": total,
        "valuation_method": product.valuation_method,
        "has_kardex": movement is not None,
    }
