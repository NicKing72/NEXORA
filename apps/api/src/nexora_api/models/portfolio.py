"""Auditable operational portfolio snapshots derived from immutable forecasts."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexora_api.db.base import Base
from nexora_api.db.types import UTCDateTime


def utc_now() -> datetime:
    return datetime.now(UTC)


class PortfolioRun(Base):
    """One frozen portfolio evaluation over compatible Forecast Runs."""

    __tablename__ = "portfolio_runs"
    __table_args__ = (
        Index("idx_portfolio_runs_dataset_created", "dataset_id", "created_at"),
        Index("idx_portfolio_runs_cutoff", "cutoff"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=True
    )
    source_mode: Mapped[str] = mapped_column(String(20), default="official")
    cutoff: Mapped[datetime] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    calculation_version: Mapped[str] = mapped_column(String(40))
    forecast_run_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    filters_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    number_of_series: Mapped[int] = mapped_column(Integer, default=0)
    summary_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    provenance_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)

    items: Mapped[list[PortfolioItem]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class PortfolioItem(Base):
    """One ranked series and its frozen demand/operational evidence."""

    __tablename__ = "portfolio_items"
    __table_args__ = (
        Index("idx_portfolio_items_run_rank", "portfolio_run_id", "rank"),
        Index("idx_portfolio_items_risk_score", "risk_level", "priority_score"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    portfolio_run_id: Mapped[str] = mapped_column(
        ForeignKey("portfolio_runs.id", ondelete="CASCADE"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer)
    series_key: Mapped[str] = mapped_column(String(900))
    product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    family: Mapped[str | None] = mapped_column(String(255), nullable=True)
    forecast_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="RESTRICT"), nullable=True
    )
    champion: Mapped[str] = mapped_column(String(60))
    forecast_horizon: Mapped[int] = mapped_column(Integer)
    forecast_frequency: Mapped[str] = mapped_column(String(20))
    forecast_total: Mapped[float] = mapped_column(Float)
    forecast_average: Mapped[float] = mapped_column(Float)
    forecast_peak: Mapped[float] = mapped_column(Float)
    forecast_minimum: Mapped[float] = mapped_column(Float)
    forecast_variability: Mapped[float | None] = mapped_column(Float, nullable=True)
    interval_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    operational_inputs_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    current_inventory: Mapped[float | None] = mapped_column(Float, nullable=True)
    inbound_inventory: Mapped[float | None] = mapped_column(Float, nullable=True)
    safety_stock: Mapped[float | None] = mapped_column(Float, nullable=True)
    lead_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    inventory_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    coverage_status: Mapped[str] = mapped_column(String(30))
    projected_exposure: Mapped[float | None] = mapped_column(Float, nullable=True)
    operational_data_completeness: Mapped[str] = mapped_column(String(30))
    risk_level: Mapped[str] = mapped_column(String(20))
    priority_score: Mapped[float] = mapped_column(Float)
    score_status: Mapped[str] = mapped_column(String(20))
    score_components: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    priority_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    missing_inputs: Mapped[list[str]] = mapped_column(JSON, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    provenance_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)

    run: Mapped[PortfolioRun] = relationship(back_populates="items")
