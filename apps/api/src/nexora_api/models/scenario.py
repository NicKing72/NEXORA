"""Auditable scenario simulations derived from immutable forecast runs."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexora_api.db.base import Base
from nexora_api.db.types import UTCDateTime


def utc_now() -> datetime:
    return datetime.now(UTC)


class ScenarioRun(Base):
    """One conditional simulation anchored to an immutable ForecastRun."""

    __tablename__ = "scenario_runs"
    __table_args__ = (
        Index("idx_scenario_runs_forecast_created", "forecast_run_id", "created_at"),
        Index("idx_scenario_runs_dataset_status", "dataset_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    forecast_run_id: Mapped[str] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="RESTRICT"), nullable=False
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    frequency: Mapped[str] = mapped_column(String(20))
    horizon: Mapped[int] = mapped_column(Integer)
    champion_model: Mapped[str] = mapped_column(String(50))
    data_cutoff: Mapped[datetime] = mapped_column(UTCDateTime())
    selection_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    baseline_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    provenance_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    summary_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    executed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    assumptions: Mapped[list[ScenarioAssumption]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    points: Mapped[list[ScenarioPoint]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    audit_entries: Mapped[list[ScenarioAudit]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class ScenarioAssumption(Base):
    """One ordered, explicit and provenance-aware scenario assumption."""

    __tablename__ = "scenario_assumptions"
    __table_args__ = (
        Index("idx_scenario_assumptions_run_order", "scenario_run_id", "order_index"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario_run_id: Mapped[str] = mapped_column(
        ForeignKey("scenario_runs.id", ondelete="CASCADE"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer)
    assumption_type: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(160))
    start_at: Mapped[datetime] = mapped_column(UTCDateTime())
    end_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    scope_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    magnitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(24))
    application_method: Mapped[str] = mapped_column(String(40))
    source_type: Mapped[str] = mapped_column(String(30))
    context_signal_id: Mapped[str | None] = mapped_column(
        ForeignKey("context_signals.id", ondelete="RESTRICT"), nullable=True
    )
    context_impact_estimate_id: Mapped[str | None] = mapped_column(
        ForeignKey("context_impact_estimates.id", ondelete="RESTRICT"), nullable=True
    )
    provenance_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)

    run: Mapped[ScenarioRun] = relationship(back_populates="assumptions")


class ScenarioPoint(Base):
    """One future baseline/scenario comparison point."""

    __tablename__ = "scenario_points"
    __table_args__ = (
        Index("idx_scenario_points_run_timestamp", "scenario_run_id", "timestamp", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_run_id: Mapped[str] = mapped_column(
        ForeignKey("scenario_runs.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime())
    baseline: Mapped[float] = mapped_column(Float)
    scenario: Mapped[float] = mapped_column(Float)
    absolute_delta: Mapped[float] = mapped_column(Float)
    relative_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    lower_80: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_80: Mapped[float | None] = mapped_column(Float, nullable=True)
    lower_95: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_95: Mapped[float | None] = mapped_column(Float, nullable=True)
    active_assumption_ids: Mapped[list[str]] = mapped_column(JSON, default=list)

    run: Mapped[ScenarioRun] = relationship(back_populates="points")


class ScenarioAudit(Base):
    """Append-only audit record for scenario lifecycle operations."""

    __tablename__ = "scenario_audit"
    __table_args__ = (Index("idx_scenario_audit_run_created", "scenario_run_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_run_id: Mapped[str] = mapped_column(
        ForeignKey("scenario_runs.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(40))
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    run: Mapped[ScenarioRun] = relationship(back_populates="audit_entries")
