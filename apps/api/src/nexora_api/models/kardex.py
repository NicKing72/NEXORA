"""Persistent product master and auditable Kardex ledger."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexora_api.db.base import Base
from nexora_api.db.types import UTCDateTime


def utc_now() -> datetime:
    return datetime.now(UTC)


class InventoryProduct(Base):
    """Master data for one stock-tracked SKU; balances are derived from movements."""

    __tablename__ = "inventory_products"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_inventory_products_sku"),
        UniqueConstraint("barcode", name="uq_inventory_products_barcode"),
        Index("idx_inventory_products_name", "name"),
        Index("idx_inventory_products_active", "active"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(128), nullable=True)
    barcode_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    unit_of_measure: Mapped[str] = mapped_column(String(30), default="unit")
    warehouse: Mapped[str | None] = mapped_column(String(120), nullable=True)
    supplier: Mapped[str | None] = mapped_column(String(180), nullable=True)
    forecast_product_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    initial_stock: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    initial_unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    valuation_method: Mapped[str] = mapped_column(String(24), default="WEIGHTED_AVERAGE")
    minimum_stock: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    maximum_stock: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    reorder_reference: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    movements: Mapped[list[KardexMovement]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="KardexMovement.timestamp, KardexMovement.created_at, KardexMovement.id",
    )


class KardexMovement(Base):
    """Append-only inventory transaction with the resulting balance snapshot."""

    __tablename__ = "kardex_movements"
    __table_args__ = (
        Index("idx_kardex_product_time", "product_id", "timestamp", "created_at"),
        Index("idx_kardex_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("inventory_products.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(40), nullable=False)
    direction: Mapped[str] = mapped_column(String(3), nullable=False)
    document_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    warehouse: Mapped[str | None] = mapped_column(String(120), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    valuation_method: Mapped[str] = mapped_column(String(24), nullable=False)
    balance_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    balance_unit_cost: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    balance_total: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    product: Mapped[InventoryProduct] = relationship(back_populates="movements")
    outbound_allocations: Mapped[list[KardexAllocation]] = relationship(
        foreign_keys="KardexAllocation.outbound_movement_id",
        back_populates="outbound_movement",
        cascade="all, delete-orphan",
    )
    inbound_allocations: Mapped[list[KardexAllocation]] = relationship(
        foreign_keys="KardexAllocation.inbound_movement_id",
        back_populates="inbound_movement",
        cascade="all, delete-orphan",
    )


class KardexAllocation(Base):
    """FIFO evidence linking an outbound movement to consumed inbound layers."""

    __tablename__ = "kardex_allocations"
    __table_args__ = (
        Index("idx_kardex_alloc_outbound", "outbound_movement_id"),
        Index("idx_kardex_alloc_inbound", "inbound_movement_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    outbound_movement_id: Mapped[str] = mapped_column(
        ForeignKey("kardex_movements.id", ondelete="CASCADE"), nullable=False
    )
    inbound_movement_id: Mapped[str] = mapped_column(
        ForeignKey("kardex_movements.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    outbound_movement: Mapped[KardexMovement] = relationship(
        foreign_keys=[outbound_movement_id], back_populates="outbound_allocations"
    )
    inbound_movement: Mapped[KardexMovement] = relationship(
        foreign_keys=[inbound_movement_id], back_populates="inbound_allocations"
    )
