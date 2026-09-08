"""Typed contracts for product master, Kardex movements and valuation evidence."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, root_validator, validator

BarcodeType = Literal["EAN13", "EAN8", "UPC_A", "UPC_E", "CODE128", "QR", "OTHER"]
ValuationMethod = Literal["FIFO", "WEIGHTED_AVERAGE"]
MovementSource = Literal["manual", "barcode", "import", "system"]
MovementType = Literal[
    "OPENING_BALANCE",
    "PURCHASE_IN",
    "PRODUCTION_IN",
    "CUSTOMER_RETURN_IN",
    "TRANSFER_IN",
    "SALE_OUT",
    "PRODUCTION_CONSUMPTION_OUT",
    "SUPPLIER_RETURN_OUT",
    "TRANSFER_OUT",
    "POSITIVE_ADJUSTMENT",
    "NEGATIVE_ADJUSTMENT",
]


def _utc(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class InventoryProductCreate(BaseModel):
    sku: str = Field(..., min_length=1, max_length=64)
    barcode: str | None = Field(None, max_length=128)
    barcode_type: BarcodeType | None = None
    name: str = Field(..., min_length=1, max_length=180)
    description: str | None = Field(None, max_length=1200)
    category: str | None = Field(None, max_length=120)
    unit_of_measure: str = Field("unit", min_length=1, max_length=30)
    warehouse: str | None = Field(None, max_length=120)
    supplier: str | None = Field(None, max_length=180)
    forecast_product_reference: str | None = Field(None, max_length=255)
    active: bool = True
    initial_stock: Decimal | None = Field(None, ge=0, decimal_places=6)
    initial_unit_cost: Decimal | None = Field(None, ge=0, decimal_places=6)
    valuation_method: ValuationMethod = "WEIGHTED_AVERAGE"
    minimum_stock: Decimal | None = Field(None, ge=0, decimal_places=6)
    maximum_stock: Decimal | None = Field(None, ge=0, decimal_places=6)
    reorder_reference: Decimal | None = Field(None, ge=0, decimal_places=6)

    @validator("sku")
    def normalize_sku(cls, value: str) -> str:
        return value.strip().upper()

    @validator(
        "barcode",
        "name",
        "description",
        "category",
        "unit_of_measure",
        "warehouse",
        "supplier",
        "forecast_product_reference",
        pre=True,
    )
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @root_validator(skip_on_failure=True)
    def validate_initial_and_limits(cls, values: dict[str, object]) -> dict[str, object]:
        stock = values.get("initial_stock")
        cost = values.get("initial_unit_cost")
        if isinstance(stock, Decimal) and stock > 0 and cost is None:
            raise ValueError("initial_unit_cost is required when initial_stock is positive")
        minimum, maximum = values.get("minimum_stock"), values.get("maximum_stock")
        if isinstance(minimum, Decimal) and isinstance(maximum, Decimal) and minimum > maximum:
            raise ValueError("minimum_stock cannot exceed maximum_stock")
        barcode, kind = values.get("barcode"), values.get("barcode_type")
        if barcode and kind is None:
            values["barcode_type"] = "OTHER"
        return values


class InventoryProductUpdate(BaseModel):
    barcode: str | None = Field(None, max_length=128)
    barcode_type: BarcodeType | None = None
    name: str | None = Field(None, min_length=1, max_length=180)
    description: str | None = Field(None, max_length=1200)
    category: str | None = Field(None, max_length=120)
    unit_of_measure: str | None = Field(None, min_length=1, max_length=30)
    warehouse: str | None = Field(None, max_length=120)
    supplier: str | None = Field(None, max_length=180)
    forecast_product_reference: str | None = Field(None, max_length=255)
    active: bool | None = None
    minimum_stock: Decimal | None = Field(None, ge=0, decimal_places=6)
    maximum_stock: Decimal | None = Field(None, ge=0, decimal_places=6)
    reorder_reference: Decimal | None = Field(None, ge=0, decimal_places=6)


class KardexMovementCreate(BaseModel):
    product_id: str
    timestamp: datetime
    movement_type: MovementType
    document_reference: str | None = Field(None, max_length=160)
    warehouse: str | None = Field(None, max_length=120)
    quantity: Decimal = Field(..., ge=0, decimal_places=6)
    unit_cost: Decimal | None = Field(None, ge=0, decimal_places=6)
    note: str | None = Field(None, max_length=1200)
    source: MovementSource = "manual"

    @validator("product_id")
    def validate_product_id(cls, value: str) -> str:
        return str(UUID(value))

    @validator("timestamp", pre=True)
    def normalize_timestamp(cls, value: datetime | str) -> datetime:
        return _utc(value)

    @validator("document_reference", "warehouse", "note", pre=True)
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @root_validator(skip_on_failure=True)
    def validate_quantity(cls, values: dict[str, object]) -> dict[str, object]:
        quantity = values.get("quantity")
        if isinstance(quantity, Decimal) and quantity == 0:
            if values.get("movement_type") != "OPENING_BALANCE":
                raise ValueError("movement quantity must be positive")
        return values


class KardexAllocationResponse(BaseModel):
    inbound_movement_id: str
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal


class KardexMovementResponse(BaseModel):
    id: str
    product_id: str
    timestamp: datetime
    movement_type: str
    direction: str
    document_reference: str | None = None
    warehouse: str | None = None
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    note: str | None = None
    source: str
    valuation_method: str
    balance_quantity: Decimal
    balance_unit_cost: Decimal
    balance_total: Decimal
    created_at: datetime
    allocations: list[KardexAllocationResponse] = Field(default_factory=list)


class KardexBalanceResponse(BaseModel):
    product_id: str
    sku: str
    as_of: datetime | None = None
    movement_id: str | None = None
    quantity: Decimal | None = None
    unit_cost: Decimal | None = None
    total_value: Decimal | None = None
    valuation_method: str
    has_kardex: bool


class InventoryProductResponse(BaseModel):
    id: str
    sku: str
    barcode: str | None = None
    barcode_type: str | None = None
    name: str
    description: str | None = None
    category: str | None = None
    unit_of_measure: str
    warehouse: str | None = None
    supplier: str | None = None
    forecast_product_reference: str | None = None
    active: bool
    initial_stock: Decimal | None = None
    initial_unit_cost: Decimal | None = None
    valuation_method: str
    minimum_stock: Decimal | None = None
    maximum_stock: Decimal | None = None
    reorder_reference: Decimal | None = None
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    stock_quantity: Decimal | None = None
    stock_unit_cost: Decimal | None = None
    stock_value: Decimal | None = None
    last_movement_at: datetime | None = None


class KardexMovementPreview(BaseModel):
    product_id: str
    movement_type: str
    direction: str
    previous_quantity: Decimal
    movement_quantity: Decimal
    resulting_quantity: Decimal
    previous_value: Decimal
    movement_value: Decimal
    resulting_value: Decimal
    effective_unit_cost: Decimal
    valuation_method: str
    allocations: list[KardexAllocationResponse] = Field(default_factory=list)


class KardexSummaryResponse(BaseModel):
    active_skus: int
    units_in_stock: Decimal
    inventory_value: Decimal
    out_of_stock: int
    below_minimum: int
    movements_today: int
    inbound_quantity: Decimal
    outbound_quantity: Decimal
    latest_movements: list[KardexMovementResponse]


class KardexDemoResponse(BaseModel):
    products: list[InventoryProductResponse]
    summary: KardexSummaryResponse
    demo_barcodes: dict[str, str]
