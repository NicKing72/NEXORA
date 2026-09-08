"""Product-master workflows and balance-enriched serialization."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.kardex import InventoryProduct
from nexora_api.schemas.kardex import InventoryProductCreate, InventoryProductUpdate
from nexora_api.services.kardex.balances import current_values
from nexora_api.services.kardex.validation import validate_barcode, validate_bounds


def require_product(db: Session, product_id: str) -> InventoryProduct:
    product = db.query(InventoryProduct).filter(InventoryProduct.id == product_id).one_or_none()
    if product is None:
        raise DataStudioError("kardex_product_not_found", "El producto solicitado no existe.", 404)
    return product


def create_product(
    db: Session,
    payload: InventoryProductCreate,
    *,
    product_id: str | None = None,
    is_demo: bool = False,
    commit: bool = True,
) -> InventoryProduct:
    validate_barcode(payload.barcode, payload.barcode_type)
    validate_bounds(payload.minimum_stock, payload.maximum_stock)
    now = datetime.now(UTC)
    product = InventoryProduct(
        id=product_id or str(uuid4()),
        sku=payload.sku,
        barcode=payload.barcode,
        barcode_type=payload.barcode_type,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        unit_of_measure=payload.unit_of_measure,
        warehouse=payload.warehouse,
        supplier=payload.supplier,
        forecast_product_reference=payload.forecast_product_reference,
        active=payload.active,
        initial_stock=payload.initial_stock,
        initial_unit_cost=payload.initial_unit_cost,
        valuation_method=payload.valuation_method,
        minimum_stock=payload.minimum_stock,
        maximum_stock=payload.maximum_stock,
        reorder_reference=payload.reorder_reference,
        is_demo=is_demo,
        created_at=now,
        updated_at=now,
    )
    db.add(product)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise DataStudioError(
            "kardex_product_conflict", "El SKU o código de barras ya está registrado.", 409
        ) from error
    if commit:
        db.commit()
        db.refresh(product)
    return product


def create_product_with_opening(
    db: Session,
    payload: InventoryProductCreate,
    *,
    product_id: str | None = None,
    is_demo: bool = False,
    opening_timestamp: datetime | None = None,
) -> InventoryProduct:
    product = create_product(
        db, payload, product_id=product_id, is_demo=is_demo, commit=False
    )
    if payload.initial_stock is not None:
        from nexora_api.schemas.kardex import KardexMovementCreate
        from nexora_api.services.kardex.movements import register_movement

        register_movement(
            db,
            KardexMovementCreate(
                product_id=product.id,
                timestamp=opening_timestamp or datetime.now(UTC),
                movement_type="OPENING_BALANCE",
                document_reference="SALDO-INICIAL",
                warehouse=product.warehouse,
                quantity=payload.initial_stock,
                unit_cost=payload.initial_unit_cost or 0,
                note="Saldo inicial declarado al crear el producto.",
                source="system",
            ),
            commit=False,
        )
    db.commit()
    return require_product(db, product.id)


def update_product(
    db: Session, product_id: str, payload: InventoryProductUpdate
) -> InventoryProduct:
    product = require_product(db, product_id)
    values = payload.dict(exclude_unset=True)
    barcode = values.get("barcode", product.barcode)
    barcode_type = values.get("barcode_type", product.barcode_type)
    validate_barcode(barcode, barcode_type)
    validate_bounds(
        values.get("minimum_stock", product.minimum_stock),
        values.get("maximum_stock", product.maximum_stock),
    )
    for key, value in values.items():
        setattr(product, key, value)
    product.updated_at = datetime.now(UTC)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise DataStudioError(
            "kardex_product_conflict", "El código de barras ya está registrado.", 409
        ) from error
    db.refresh(product)
    return product


def list_products(
    db: Session, *, query: str | None = None, active: bool | None = None
) -> list[InventoryProduct]:
    result = db.query(InventoryProduct)
    if query:
        pattern = f"%{query.strip()}%"
        result = result.filter(
            or_(
                InventoryProduct.sku.ilike(pattern),
                InventoryProduct.barcode.ilike(pattern),
                InventoryProduct.name.ilike(pattern),
            )
        )
    if active is not None:
        result = result.filter(InventoryProduct.active.is_(active))
    return result.order_by(InventoryProduct.sku, InventoryProduct.id).limit(500).all()


def lookup_product(db: Session, identifier: str) -> InventoryProduct:
    normalized = identifier.strip()
    product = (
        db.query(InventoryProduct)
        .filter(
            or_(
                InventoryProduct.sku == normalized.upper(),
                InventoryProduct.barcode == normalized,
                InventoryProduct.id == normalized,
            )
        )
        .one_or_none()
    )
    if product is None:
        raise DataStudioError("kardex_product_not_found", "Código no registrado.", 404)
    return product


def serialize_product(db: Session, product: InventoryProduct) -> dict[str, object]:
    quantity, unit_cost, value, movement = current_values(db, product.id)
    return {
        "id": product.id,
        "sku": product.sku,
        "barcode": product.barcode,
        "barcode_type": product.barcode_type,
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "unit_of_measure": product.unit_of_measure,
        "warehouse": product.warehouse,
        "supplier": product.supplier,
        "forecast_product_reference": product.forecast_product_reference,
        "active": product.active,
        "initial_stock": product.initial_stock,
        "initial_unit_cost": product.initial_unit_cost,
        "valuation_method": product.valuation_method,
        "minimum_stock": product.minimum_stock,
        "maximum_stock": product.maximum_stock,
        "reorder_reference": product.reorder_reference,
        "is_demo": product.is_demo,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        "stock_quantity": quantity,
        "stock_unit_cost": unit_cost,
        "stock_value": value,
        "last_movement_at": movement.timestamp if movement else None,
    }
