"""Reproducible, isolated Kardex demonstration data."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy.orm import Session

from nexora_api.models.kardex import InventoryProduct
from nexora_api.schemas.kardex import InventoryProductCreate, KardexMovementCreate
from nexora_api.services.kardex.movements import register_movement
from nexora_api.services.kardex.products import create_product
from nexora_api.services.kardex.summary import build_summary

NAMESPACE = UUID("8de0f3f1-31b3-4e68-9e1c-a8429141f4bc")
DEMO_BARCODES = {
    "BEB-001": "2000000000015",
    "ALI-002": "2000000000022",
    "HOG-003": "2000000000039",
}


def _id(kind: str, key: str) -> str:
    return str(uuid5(NAMESPACE, f"{kind}:{key}"))


def _timestamp(day: int, hour: int = 9) -> datetime:
    return datetime(2026, 8, day, hour, tzinfo=UTC)


def regenerate_demo(db: Session) -> dict[str, object]:
    for product in db.query(InventoryProduct).filter(InventoryProduct.is_demo.is_(True)).all():
        db.delete(product)
    db.commit()
    definitions = [
        ("BEB-001", "Bebida 500 ml", "Bebidas", "WEIGHTED_AVERAGE", Decimal("40")),
        ("ALI-002", "Alimento ejemplo", "Alimentos", "FIFO", Decimal("25")),
        ("HOG-003", "Producto hogar", "Hogar", "WEIGHTED_AVERAGE", Decimal("20")),
    ]
    products: list[InventoryProduct] = []
    for sku, name, category, method, minimum in definitions:
        products.append(
            create_product(
                db,
                InventoryProductCreate(
                    sku=sku,
                    barcode=DEMO_BARCODES[sku],
                    barcode_type="EAN13",
                    name=name,
                    category=category,
                    unit_of_measure="unidad",
                    warehouse="Lima Centro",
                    supplier="Proveedor demo",
                    forecast_product_reference="NX-101" if sku == "BEB-001" else None,
                    valuation_method=method,
                    minimum_stock=minimum,
                    maximum_stock=Decimal("500"),
                ),
                product_id=_id("product", sku),
                is_demo=True,
                commit=False,
            )
        )
    db.commit()
    movements = {
        "BEB-001": [
            (1, "OPENING_BALANCE", "100", "10", "DEMO-BEB-01"),
            (3, "PURCHASE_IN", "50", "12", "DEMO-BEB-02"),
            (5, "SALE_OUT", "30", None, "DEMO-BEB-03"),
        ],
        "ALI-002": [
            (1, "OPENING_BALANCE", "100", "8", "DEMO-ALI-01"),
            (3, "PURCHASE_IN", "50", "9.5", "DEMO-ALI-02"),
            (5, "SALE_OUT", "120", None, "DEMO-ALI-03"),
        ],
        "HOG-003": [
            (1, "OPENING_BALANCE", "80", "15", "DEMO-HOG-01"),
            (6, "NEGATIVE_ADJUSTMENT", "5", None, "DEMO-HOG-02"),
        ],
    }
    by_sku = {product.sku: product for product in products}
    for sku, entries in movements.items():
        for day, kind, quantity, cost, document in entries:
            register_movement(
                db,
                KardexMovementCreate(
                    product_id=by_sku[sku].id,
                    timestamp=_timestamp(day),
                    movement_type=kind,
                    document_reference=document,
                    warehouse="Lima Centro",
                    quantity=Decimal(quantity),
                    unit_cost=Decimal(cost) if cost is not None else None,
                    note="Movimiento determinístico de demostración.",
                    source="system",
                ),
                movement_id=_id("movement", document),
                created_at=_timestamp(day, 10),
                commit=False,
            )
        db.commit()
    from nexora_api.services.kardex.products import serialize_product

    return {
        "products": [serialize_product(db, product) for product in products],
        "summary": build_summary(db),
        "demo_barcodes": DEMO_BARCODES,
    }
