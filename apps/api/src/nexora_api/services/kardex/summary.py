"""Portfolio-level stock totals derived exclusively from confirmed movements."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from nexora_api.models.kardex import InventoryProduct
from nexora_api.services.kardex.balances import current_values
from nexora_api.services.kardex.movements import list_movements, serialize_movement
from nexora_api.services.kardex.validation import ZERO, quantize


def build_summary(db: Session) -> dict[str, object]:
    products = (
        db.query(InventoryProduct)
        .filter(InventoryProduct.active.is_(True))
        .order_by(InventoryProduct.sku)
        .all()
    )
    units, value = ZERO, ZERO
    out_of_stock = 0
    below_minimum = 0
    for product in products:
        quantity, _, total, movement = current_values(db, product.id)
        if movement is None:
            continue
        units = quantize(units + (quantity or ZERO))
        value = quantize(value + (total or ZERO))
        if quantity == ZERO:
            out_of_stock += 1
        if product.minimum_stock is not None and quantity is not None:
            below_minimum += int(quantity < Decimal(product.minimum_stock))
    today = datetime.now(UTC).date()
    movements = list_movements(db, limit=1000)
    inbound = quantize(
        sum((movement.quantity for movement in movements if movement.direction == "in"), ZERO)
    )
    outbound = quantize(
        sum((movement.quantity for movement in movements if movement.direction == "out"), ZERO)
    )
    return {
        "active_skus": len(products),
        "units_in_stock": units,
        "inventory_value": value,
        "out_of_stock": out_of_stock,
        "below_minimum": below_minimum,
        "movements_today": sum(movement.timestamp.date() == today for movement in movements),
        "inbound_quantity": inbound,
        "outbound_quantity": outbound,
        "latest_movements": [serialize_movement(movement) for movement in movements[:8]],
    }
