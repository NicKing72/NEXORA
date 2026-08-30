"""Auditable quantitative SCOR diagnostic persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexora_api.db.base import Base
from nexora_api.db.types import UTCDateTime


def utc_now() -> datetime:
    return datetime.now(UTC)


class ScorAssessmentRun(Base):
    __tablename__ = "scor_assessment_runs"
    __table_args__ = (
        Index("idx_scor_assessment_created", "created_at"),
        Index("idx_scor_assessment_dataset_status", "source_dataset_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    company_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    source_dataset_id: Mapped[str | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=True
    )
    forecast_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="RESTRICT"), nullable=True
    )
    benchmark_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("scor_benchmark_profiles.id", ondelete="RESTRICT"), nullable=True
    )
    period_start: Mapped[datetime] = mapped_column(UTCDateTime())
    period_end: Mapped[datetime] = mapped_column(UTCDateTime())
    cutoff: Mapped[datetime] = mapped_column(UTCDateTime())
    status: Mapped[str] = mapped_column(String(30), default="draft")
    source_name: Mapped[str] = mapped_column(String(180))
    source_metadata: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    summary_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    criticality_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    algorithm_version: Mapped[str] = mapped_column(String(30), default="scor_diagnostic_v1")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    calculated_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    metric_inputs: Mapped[list[ScorMetricInput]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    metric_results: Mapped[list[ScorMetricResult]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    process_results: Mapped[list[ScorProcessResult]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    audit_entries: Mapped[list[ScorAudit]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class ScorMetricInput(Base):
    __tablename__ = "scor_metric_inputs"
    __table_args__ = (
        Index("idx_scor_metric_input_assessment_metric", "assessment_id", "metric_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("scor_assessment_runs.id", ondelete="CASCADE"), nullable=False
    )
    metric_id: Mapped[str] = mapped_column(String(10))
    values_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    monthly_values_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(180), default="manual")
    provenance_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    not_applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    assessment: Mapped[ScorAssessmentRun] = relationship(back_populates="metric_inputs")


class ScorMetricResult(Base):
    __tablename__ = "scor_metric_results"
    __table_args__ = (
        Index(
            "idx_scor_metric_result_assessment_metric", "assessment_id", "metric_id", unique=True
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("scor_assessment_runs.id", ondelete="CASCADE"), nullable=False
    )
    metric_id: Mapped[str] = mapped_column(String(10))
    process: Mapped[str] = mapped_column(String(12))
    attribute: Mapped[str] = mapped_column(String(60))
    method: Mapped[str] = mapped_column(String(40))
    formula: Mapped[str] = mapped_column(Text)
    substituted_formula: Mapped[str] = mapped_column(Text, default="")
    inputs_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    numerator: Mapped[float | None] = mapped_column(Float, nullable=True)
    denominator: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    ratio_decimal: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(40))
    evidence_status: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculation_details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    target_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    gap_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    algorithm_version: Mapped[str] = mapped_column(String(30), default="scor_diagnostic_v1")

    assessment: Mapped[ScorAssessmentRun] = relationship(back_populates="metric_results")


class ScorProcessResult(Base):
    __tablename__ = "scor_process_results"
    __table_args__ = (
        Index("idx_scor_process_assessment_process", "assessment_id", "process", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("scor_assessment_runs.id", ondelete="CASCADE"), nullable=False
    )
    process: Mapped[str] = mapped_column(String(12))
    metrics_total: Mapped[int] = mapped_column(Integer)
    metrics_complete: Mapped[int] = mapped_column(Integer)
    metrics_insufficient: Mapped[int] = mapped_column(Integer)
    metrics_not_applicable: Mapped[int] = mapped_column(Integer)
    metrics_evaluable: Mapped[int] = mapped_column(Integer, default=0)
    data_coverage: Mapped[float] = mapped_column(Float, default=0.0)
    benchmark_coverage: Mapped[float] = mapped_column(Float, default=0.0)
    weighted_gap_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[str] = mapped_column(String(30), default="insufficient")
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)

    assessment: Mapped[ScorAssessmentRun] = relationship(back_populates="process_results")


class ScorBenchmarkProfile(Base):
    __tablename__ = "scor_benchmark_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    profile_type: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(180))
    notes: Mapped[str] = mapped_column(Text, default="")
    is_official_scor: Mapped[bool] = mapped_column(Boolean, default=False)
    minimum_process_coverage: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    targets: Mapped[list[ScorBenchmarkTarget]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class ScorBenchmarkTarget(Base):
    __tablename__ = "scor_benchmark_targets"
    __table_args__ = (
        Index("idx_scor_target_profile_metric", "profile_id", "metric_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("scor_benchmark_profiles.id", ondelete="CASCADE"), nullable=False
    )
    metric_id: Mapped[str] = mapped_column(String(10))
    direction: Mapped[str] = mapped_column(String(30))
    target: Mapped[float | None] = mapped_column(Float, nullable=True)
    optional_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    optional_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(180))
    notes: Mapped[str] = mapped_column(Text, default="")

    profile: Mapped[ScorBenchmarkProfile] = relationship(back_populates="targets")


class ScorAudit(Base):
    __tablename__ = "scor_audit"
    __table_args__ = (Index("idx_scor_audit_assessment_created", "assessment_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("scor_assessment_runs.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(50))
    details_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    assessment: Mapped[ScorAssessmentRun] = relationship(back_populates="audit_entries")
