"""Append-only movement registration and auditable valuation snapshots."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.kardex import KardexAllocation, KardexMovement
from nexora_api.schemas.kardex import KardexMovementCreate
from nexora_api.services.kardex.balances import current_values
from nexora_api.services.kardex.fifo import consume_fifo
from nexora_api.services.kardex.products import require_product
from nexora_api.services.kardex.validation import ZERO, movement_direction, quantize
from nexora_api.services.kardex.weighted_average import weighted_average_in, weighted_average_out


def _draft(db: Session, payload: KardexMovementCreate) -> dict[str, object]:
    product = require_product(db, payload.product_id)
    if not product.active:
        raise DataStudioError("kardex_product_inactive", "El producto está inactivo.")
    if payload.timestamp > datetime.now(UTC) + timedelta(minutes=5):
        raise DataStudioError(
            "kardex_future_movement", "Un movimiento real no puede registrarse en el futuro."
        )
    previous_quantity, previous_unit_cost, previous_value, previous = current_values(
        db, product.id
    )
    prior_quantity = previous_quantity or ZERO
    prior_unit_cost = previous_unit_cost or ZERO
    prior_value = previous_value or ZERO
    if previous is not None and payload.timestamp < previous.timestamp:
        raise DataStudioError(
            "kardex_backdated_movement",
            "El movimiento no puede anteceder al último movimiento confirmado.",
        )
    if payload.movement_type == "OPENING_BALANCE" and previous is not None:
        raise DataStudioError(
            "kardex_opening_balance_exists", "El saldo inicial solo puede ser el primer movimiento."
        )
    direction = movement_direction(payload.movement_type)
    quantity = quantize(payload.quantity)
    if direction == "out" and quantity > prior_quantity:
        raise DataStudioError(
            "kardex_negative_stock",
            f"La salida supera el stock disponible de {prior_quantity} unidades.",
        )
    allocations: list[dict[str, Decimal | str]] = []
    if direction == "in":
        if payload.unit_cost is None:
            raise DataStudioError(
                "kardex_unit_cost_required", "Las entradas requieren un costo unitario explícito."
            )
        unit_cost = quantize(payload.unit_cost)
        quantity_after, balance_unit_cost, value_after, movement_total = weighted_average_in(
            prior_quantity, prior_value, quantity, unit_cost
        )
    elif product.valuation_method == "FIFO":
        allocations, movement_total = consume_fifo(db, product.id, quantity)
        if quantize(sum((Decimal(item["quantity"]) for item in allocations), ZERO)) != quantity:
            raise DataStudioError(
                "kardex_fifo_layers_incomplete", "Las capas FIFO no cubren la salida."
            )
        unit_cost = quantize(movement_total / quantity)
        quantity_after = quantize(prior_quantity - quantity)
        value_after = ZERO if quantity_after == ZERO else quantize(prior_value - movement_total)
        balance_unit_cost = (
            ZERO if quantity_after == ZERO else quantize(value_after / quantity_after)
        )
    else:
        quantity_after, balance_unit_cost, value_after, movement_total = weighted_average_out(
            prior_quantity, prior_unit_cost, prior_value, quantity
        )
        unit_cost = quantize(movement_total / quantity)
    return {
        "product": product,
        "direction": direction,
        "previous_quantity": prior_quantity,
        "previous_unit_cost": prior_unit_cost,
        "previous_value": prior_value,
        "quantity": quantity,
        "unit_cost": unit_cost,
        "movement_total": movement_total,
        "quantity_after": quantity_after,
        "balance_unit_cost": balance_unit_cost,
        "value_after": value_after,
        "allocations": allocations,
    }


def preview_movement(db: Session, payload: KardexMovementCreate) -> dict[str, object]:
    draft = _draft(db, payload)
    return {
        "product_id": payload.product_id,
        "movement_type": payload.movement_type,
        "direction": draft["direction"],
        "previous_quantity": draft["previous_quantity"],
        "movement_quantity": draft["quantity"],
        "resulting_quantity": draft["quantity_after"],
        "previous_value": draft["previous_value"],
        "movement_value": draft["movement_total"],
        "resulting_value": draft["value_after"],
        "effective_unit_cost": draft["unit_cost"],
        "valuation_method": draft["product"].valuation_method,
        "allocations": draft["allocations"],
    }


def register_movement(
    db: Session,
    payload: KardexMovementCreate,
    *,
    movement_id: str | None = None,
    created_at: datetime | None = None,
    commit: bool = True,
) -> KardexMovement:
    draft = _draft(db, payload)
    product = draft["product"]
    movement = KardexMovement(
        id=movement_id or str(uuid4()),
        product_id=product.id,
        timestamp=payload.timestamp,
        movement_type=payload.movement_type,
        direction=draft["direction"],
        document_reference=payload.document_reference,
        warehouse=payload.warehouse or product.warehouse,
        quantity=draft["quantity"],
        unit_cost=draft["unit_cost"],
        total_cost=draft["movement_total"],
        note=payload.note,
        source=payload.source,
        valuation_method=product.valuation_method,
        balance_quantity=draft["quantity_after"],
        balance_unit_cost=draft["balance_unit_cost"],
        balance_total=draft["value_after"],
        created_at=created_at or datetime.now(UTC),
    )
    db.add(movement)
    db.flush()
    for allocation in draft["allocations"]:
        db.add(
            KardexAllocation(
                id=str(uuid4()),
                outbound_movement_id=movement.id,
                inbound_movement_id=str(allocation["inbound_movement_id"]),
                quantity=allocation["quantity"],
                unit_cost=allocation["unit_cost"],
                total_cost=allocation["total_cost"],
                created_at=movement.created_at,
            )
        )
    product.updated_at = datetime.now(UTC)
    if commit:
        db.commit()
        return require_movement(db, movement.id)
    return movement


def require_movement(db: Session, movement_id: str) -> KardexMovement:
    movement = (
        db.query(KardexMovement)
        .options(selectinload(KardexMovement.outbound_allocations))
        .filter(KardexMovement.id == movement_id)
        .one_or_none()
    )
    if movement is None:
        raise DataStudioError("kardex_movement_not_found", "El movimiento no existe.", 404)
    return movement


def list_movements(
    db: Session,
    *,
    product_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 500,
) -> list[KardexMovement]:
    query = db.query(KardexMovement).options(selectinload(KardexMovement.outbound_allocations))
    if product_id:
        require_product(db, product_id)
        query = query.filter(KardexMovement.product_id == product_id)
    if date_from:
        query = query.filter(KardexMovement.timestamp >= date_from)
    if date_to:
        query = query.filter(KardexMovement.timestamp <= date_to)
    return query.order_by(
        KardexMovement.timestamp.desc(), KardexMovement.created_at.desc(), KardexMovement.id.desc()
    ).limit(limit).all()


def serialize_movement(movement: KardexMovement) -> dict[str, object]:
    return {
        "id": movement.id,
        "product_id": movement.product_id,
        "timestamp": movement.timestamp,
        "movement_type": movement.movement_type,
        "direction": movement.direction,
        "document_reference": movement.document_reference,
        "warehouse": movement.warehouse,
        "quantity": movement.quantity,
        "unit_cost": movement.unit_cost,
        "total_cost": movement.total_cost,
        "note": movement.note,
        "source": movement.source,
        "valuation_method": movement.valuation_method,
        "balance_quantity": movement.balance_quantity,
        "balance_unit_cost": movement.balance_unit_cost,
        "balance_total": movement.balance_total,
        "created_at": movement.created_at,
        "allocations": [
            {
                "inbound_movement_id": allocation.inbound_movement_id,
                "quantity": allocation.quantity,
                "unit_cost": allocation.unit_cost,
                "total_cost": allocation.total_cost,
            }
            for allocation in movement.outbound_allocations
        ],
    }
