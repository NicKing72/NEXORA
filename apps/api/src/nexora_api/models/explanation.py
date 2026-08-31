"""Immutable, auditable explanations of persisted forecast runs."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexora_api.db.base import Base
from nexora_api.db.types import UTCDateTime


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExplanationRun(Base):
    """One frozen explanation assembled without retraining a forecast."""

    __tablename__ = "explanation_runs"
    __table_args__ = (
        Index("idx_explanation_runs_forecast_created", "forecast_run_id", "created_at"),
        Index("idx_explanation_runs_dataset_cutoff", "dataset_id", "cutoff"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    forecast_run_id: Mapped[str] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="RESTRICT"), nullable=False
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False
    )
    series_id: Mapped[str] = mapped_column(String(900))
    frequency: Mapped[str] = mapped_column(String(20))
    horizon: Mapped[int] = mapped_column(Integer)
    champion_model: Mapped[str] = mapped_column(String(60))
    cutoff: Mapped[datetime] = mapped_column(UTCDateTime())
    version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="completed")
    created_from: Mapped[str] = mapped_column(String(30), default="manual")
    source_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    limitations_snapshot: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    evidence: Mapped[list[ExplanationEvidence]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class ExplanationEvidence(Base):
    """A frozen source fragment used by an explanation."""

    __tablename__ = "explanation_evidence"
    __table_args__ = (
        Index("idx_explanation_evidence_run_type", "explanation_run_id", "evidence_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    explanation_run_id: Mapped[str] = mapped_column(
        ForeignKey("explanation_runs.id", ondelete="CASCADE"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(String(40))
    source_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    label: Mapped[str] = mapped_column(String(180))
    value_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    metadata_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    provenance: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    run: Mapped[ExplanationRun] = relationship(back_populates="evidence")
