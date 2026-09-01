"""Immutable inventory and replenishment analysis snapshots."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexora_api.db.base import Base
from nexora_api.db.types import UTCDateTime


def utc_now() -> datetime:
    return datetime.now(UTC)


class InventoryRun(Base):
    """One auditable analysis anchored to an immutable demand trajectory."""

    __tablename__ = "inventory_runs"
    __table_args__ = (
        Index("idx_inventory_runs_forecast_created", "forecast_run_id", "created_at"),
        Index("idx_inventory_runs_cutoff", "cutoff"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=True
    )
    forecast_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="RESTRICT"), nullable=True
    )
    scenario_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("scenario_runs.id", ondelete="RESTRICT"), nullable=True
    )
    portfolio_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("portfolio_runs.id", ondelete="RESTRICT"), nullable=True
    )
    decision_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("decision_runs.id", ondelete="RESTRICT"), nullable=True
    )
    source_mode: Mapped[str] = mapped_column(String(20), default="official")
    cutoff: Mapped[datetime] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    calculation_version: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(24), default="completed")
    source_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    assumptions_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    missing_inputs: Mapped[list[str]] = mapped_column(JSON, default=list)
    scope_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    coverage_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    summary_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    provenance_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)

    items: Mapped[list[InventoryItem]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class InventoryItem(Base):
    """Frozen per-series calculations; unknown operational values remain NULL."""

    __tablename__ = "inventory_items"
    __table_args__ = (
        Index("idx_inventory_items_run_product", "inventory_run_id", "product"),
        Index("idx_inventory_items_risk", "risk_level"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    inventory_run_id: Mapped[str] = mapped_column(
        ForeignKey("inventory_runs.id", ondelete="CASCADE"), nullable=False
    )
    forecast_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    frequency: Mapped[str] = mapped_column(String(20))
    horizon: Mapped[int] = mapped_column(Integer)
    demand_source: Mapped[str] = mapped_column(String(20))
    forecast_total: Mapped[float] = mapped_column(Float)
    forecast_average: Mapped[float] = mapped_column(Float)
    inventory_on_hand: Mapped[float | None] = mapped_column(Float, nullable=True)
    inventory_in_transit: Mapped[float | None] = mapped_column(Float, nullable=True)
    safety_stock: Mapped[float | None] = mapped_column(Float, nullable=True)
    safety_stock_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
    lead_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    lead_time_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    service_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    order_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    holding_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    moq: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity: Mapped[float | None] = mapped_column(Float, nullable=True)
    physical_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    coverage_with_transit: Mapped[float | None] = mapped_column(Float, nullable=True)
    lead_time_demand: Mapped[float | None] = mapped_column(Float, nullable=True)
    reorder_point: Mapped[float | None] = mapped_column(Float, nullable=True)
    eoq: Mapped[float | None] = mapped_column(Float, nullable=True)
    projected_inventory: Mapped[float | None] = mapped_column(Float, nullable=True)
    projected_shortage: Mapped[float | None] = mapped_column(Float, nullable=True)
    projected_surplus: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_requirement: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommended_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20))
    completeness: Mapped[float] = mapped_column(Float)
    inputs_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    calculations_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    constraints_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    missing_inputs: Mapped[list[str]] = mapped_column(JSON, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    explanation_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    evidence_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)

    run: Mapped[InventoryRun] = relationship(back_populates="items")
