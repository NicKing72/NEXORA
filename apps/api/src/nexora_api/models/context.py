"""Persistence models for contextual signals and their audit trail."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexora_api.db.base import Base
from nexora_api.db.types import UTCDateTime


def utc_now() -> datetime:
    return datetime.now(UTC)


class ContextSignal(Base):
    """A temporally safe fact, plan, external forecast, or scenario assumption."""

    __tablename__ = "context_signals"
    __table_args__ = (
        Index("idx_context_signals_dataset_event", "dataset_id", "event_start"),
        Index("idx_context_signals_available", "available_at"),
        Index("idx_context_signals_family_status", "signal_family", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True
    )
    signal_family: Mapped[str] = mapped_column(String(40))
    signal_type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    event_start: Mapped[datetime] = mapped_column(UTCDateTime())
    event_end: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime())
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    source_type: Mapped[str] = mapped_column(String(20), default="manual")
    source_name: Mapped[str] = mapped_column(String(120), default="usuario/manual")
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    intensity: Mapped[float | None] = mapped_column(Float, nullable=True)
    knowledge_type: Mapped[str] = mapped_column(String(30))
    scope_type: Mapped[str] = mapped_column(String(20), default="global")
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(255), nullable=True)
    market: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column("metadata", JSON, default=dict)
    impact_status: Mapped[str] = mapped_column(String(30), default="not_estimated")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    audit_entries: Mapped[list[ContextSignalAudit]] = relationship(
        back_populates="signal", cascade="all, delete-orphan"
    )
    impact_estimates: Mapped[list[ContextImpactEstimate]] = relationship(
        back_populates="signal", cascade="all, delete-orphan"
    )


class ContextSignalAudit(Base):
    """Compact immutable record of create, update, and lifecycle operations."""

    __tablename__ = "context_signal_audit"
    __table_args__ = (Index("idx_context_audit_signal_created", "signal_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_id: Mapped[str] = mapped_column(
        ForeignKey("context_signals.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(30))
    changes: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    signal: Mapped[ContextSignal] = relationship(back_populates="audit_entries")


class ContextImpactEstimate(Base):
    """Immutable, reproducible estimate of an observed contextual association."""

    __tablename__ = "context_impact_estimates"
    __table_args__ = (
        Index("idx_context_impact_signal_estimated", "signal_id", "estimated_at"),
        Index("idx_context_impact_dataset_status", "dataset_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    signal_id: Mapped[str] = mapped_column(
        ForeignKey("context_signals.id", ondelete="CASCADE"), nullable=False
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    scope_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    frequency: Mapped[str] = mapped_column(String(20))
    method: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30))
    direction: Mapped[str] = mapped_column(String(20), default="unknown")
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    absolute_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    relative_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    event_periods: Mapped[int] = mapped_column(Integer, default=0)
    reference_periods: Mapped[int] = mapped_column(Integer, default=0)
    evidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_level: Mapped[str] = mapped_column(String(20), default="insufficient")
    data_cutoff: Mapped[datetime] = mapped_column(UTCDateTime())
    availability_cutoff: Mapped[datetime] = mapped_column(UTCDateTime())
    estimated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_breakdown: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    quality_summary: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    input_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)

    signal: Mapped[ContextSignal] = relationship(back_populates="impact_estimates")
