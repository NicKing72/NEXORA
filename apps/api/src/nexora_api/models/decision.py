"""Auditable decision-support runs, recommendations, evidence, and lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexora_api.db.base import Base
from nexora_api.db.types import UTCDateTime


def utc_now() -> datetime:
    return datetime.now(UTC)


class DecisionRun(Base):
    """One deterministic decision-support analysis over immutable sources."""

    __tablename__ = "decision_runs"
    __table_args__ = (
        Index("idx_decision_runs_forecast_created", "forecast_run_id", "created_at"),
        Index("idx_decision_runs_dataset_status", "dataset_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    forecast_run_id: Mapped[str] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="RESTRICT"), nullable=False
    )
    scenario_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("scenario_runs.id", ondelete="RESTRICT"), nullable=True
    )
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False
    )
    decision_cutoff: Mapped[datetime] = mapped_column(UTCDateTime())
    status: Mapped[str] = mapped_column(String(20), default="completed")
    source_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    summary_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    recommendations: Mapped[list[DecisionRecommendation]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class DecisionRecommendation(Base):
    """One explainable recommendation; never an executable order."""

    __tablename__ = "decision_recommendations"
    __table_args__ = (
        Index("idx_decision_recommendations_run_rank", "decision_run_id", "rank"),
        Index("idx_decision_recommendations_status_priority", "status", "priority"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    decision_run_id: Mapped[str] = mapped_column(
        ForeignKey("decision_runs.id", ondelete="CASCADE"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer)
    priority: Mapped[str] = mapped_column(String(20))
    action_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(180))
    summary: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    support_score: Mapped[float] = mapped_column(Float)
    evidence_level: Mapped[str] = mapped_column(String(20))
    scope_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    dataset_id: Mapped[str] = mapped_column(String(36))
    product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    forecast_run_id: Mapped[str] = mapped_column(String(36))
    scenario_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    context_signal_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    context_impact_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    decision_cutoff: Mapped[datetime] = mapped_column(UTCDateTime())
    status: Mapped[str] = mapped_column(String(20), default="open")
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list)
    provenance_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    run: Mapped[DecisionRun] = relationship(back_populates="recommendations")
    evidence: Mapped[list[DecisionEvidence]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )
    audit_entries: Mapped[list[DecisionAudit]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )


class DecisionEvidence(Base):
    """Immutable source snapshot supporting a recommendation."""

    __tablename__ = "decision_evidence"
    __table_args__ = (
        Index("idx_decision_evidence_recommendation_type", "recommendation_id", "evidence_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("decision_recommendations.id", ondelete="CASCADE"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    recommendation: Mapped[DecisionRecommendation] = relationship(back_populates="evidence")


class DecisionAudit(Base):
    """Append-only lifecycle audit for a recommendation."""

    __tablename__ = "decision_audit"
    __table_args__ = (
        Index("idx_decision_audit_recommendation_created", "recommendation_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("decision_recommendations.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(40))
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    recommendation: Mapped[DecisionRecommendation] = relationship(back_populates="audit_entries")
