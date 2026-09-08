"""Explicit Kardex-to-Inventory compatibility and temporal provenance."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import ForecastRun
from nexora_api.schemas.inventory import InventoryRequest
from nexora_api.services.inventory.snapshot import resolve_inputs
from nexora_api.services.kardex.balances import current_values
from nexora_api.services.kardex.products import require_product


def resolve_inventory_inputs(
    db: Session, payload: InventoryRequest, forecast: ForecastRun
) -> tuple[
    dict[str, object],
    dict[str, float | None],
    list[str],
    list[str],
    dict[str, object] | None,
]:
    snapshot, values, missing, warnings = resolve_inputs(payload.operational_inputs, payload.cutoff)
    if payload.inventory_source != "kardex":
        return snapshot, values, missing, warnings, None
    if not payload.kardex_product_id:
        raise DataStudioError(
            "inventory_kardex_product_required",
            "Selecciona un producto Kardex para utilizar su saldo.",
        )
    if payload.operational_inputs.inventory_on_hand.status == "available":
        raise DataStudioError(
            "inventory_stock_source_conflict",
            "Elige stock manual o Kardex; no declares ambas fuentes simultáneamente.",
        )
    product = require_product(db, payload.kardex_product_id)
    mismatches: list[str] = []
    product_reference = product.forecast_product_reference or product.sku
    if forecast.product and product_reference != forecast.product:
        mismatches.append("product")
    if forecast.location and product.warehouse and product.warehouse != forecast.location:
        mismatches.append("location")
    if forecast.category and product.category and product.category != forecast.category:
        mismatches.append("category")
    if mismatches:
        raise DataStudioError(
            "inventory_kardex_incompatible",
            "El producto Kardex no coincide con el alcance del Forecast Run.",
        )
    quantity, unit_cost, total, movement = current_values(
        db, product.id, cutoff=payload.cutoff
    )
    if movement is None:
        warnings.append("inventory_on_hand:kardex_without_balance")
        return snapshot, values, missing, warnings, {
            "product_id": product.id,
            "sku": product.sku,
            "has_kardex": False,
            "cutoff": payload.cutoff.isoformat(),
        }
    values["inventory_on_hand"] = float(quantity)
    if "inventory_on_hand" in missing:
        missing.remove("inventory_on_hand")
    snapshot["inventory_on_hand"] = {
        "value": float(quantity),
        "status": "available",
        "unit": product.unit_of_measure,
        "source_type": "kardex",
        "source_reference": f"{product.id}:{movement.id}",
        "available_at": movement.created_at.isoformat(),
    }
    return snapshot, values, missing, warnings, {
        "product_id": product.id,
        "sku": product.sku,
        "forecast_product_reference": product.forecast_product_reference,
        "movement_id": movement.id,
        "balance_timestamp": movement.timestamp.isoformat(),
        "available_at": movement.created_at.isoformat(),
        "quantity": float(quantity),
        "unit_cost": float(unit_cost),
        "total_value": float(total),
        "valuation_method": product.valuation_method,
        "cutoff": payload.cutoff.isoformat(),
        "has_kardex": True,
    }


def kardex_balance_available_at(
    db: Session, product_id: str, cutoff: datetime
) -> dict[str, object] | None:
    product = require_product(db, product_id)
    quantity, unit_cost, total, movement = current_values(db, product.id, cutoff=cutoff)
    if movement is None:
        return None
    return {
        "quantity": quantity,
        "unit_cost": unit_cost,
        "total_value": total,
        "movement_id": movement.id,
        "timestamp": movement.timestamp,
        "available_at": movement.created_at,
    }
