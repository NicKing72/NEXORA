"""Immutable reporting snapshots assembled from persisted NEXORA evidence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexora_api.db.base import Base
from nexora_api.db.types import UTCDateTime


def utc_now() -> datetime:
    return datetime.now(UTC)


class ReportRun(Base):
    """One reproducible report whose sources and rendered payload are frozen."""

    __tablename__ = "report_runs"
    __table_args__ = (
        Index("idx_report_runs_created", "created_at"),
        Index("idx_report_runs_forecast_cutoff", "forecast_run_id", "report_cutoff"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(24), default="completed")
    report_cutoff: Mapped[datetime] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    calculation_version: Mapped[str] = mapped_column(String(40))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    dataset_id: Mapped[str | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=True
    )
    forecast_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="RESTRICT"), nullable=True
    )
    scenario_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("scenario_runs.id", ondelete="RESTRICT"), nullable=True
    )
    scor_assessment_id: Mapped[str | None] = mapped_column(
        ForeignKey("scor_assessment_runs.id", ondelete="RESTRICT"), nullable=True
    )
    portfolio_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("portfolio_runs.id", ondelete="RESTRICT"), nullable=True
    )
    decision_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("decision_runs.id", ondelete="RESTRICT"), nullable=True
    )
    explanation_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("explanation_runs.id", ondelete="RESTRICT"), nullable=True
    )
    source_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    report_payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list)

    sections: Mapped[list[ReportSection]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class ReportSection(Base):
    """One ordered report section with frozen evidence references."""

    __tablename__ = "report_sections"
    __table_args__ = (
        Index("idx_report_sections_run_position", "report_run_id", "position", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_run_id: Mapped[str] = mapped_column(
        ForeignKey("report_runs.id", ondelete="CASCADE"), nullable=False
    )
    section_type: Mapped[str] = mapped_column(String(50))
    position: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    source_references: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    completeness: Mapped[str] = mapped_column(String(30), default="complete")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    run: Mapped[ReportRun] = relationship(back_populates="sections")
