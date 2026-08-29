"""Persistence models for datasets, mappings, quality, and lineage."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexora_api.db.base import Base
from nexora_api.db.types import UTCDateTime


def utc_now() -> datetime:
    return datetime.now(UTC)


class Dataset(Base):
    """Metadata for one imported source file or generated demo dataset."""

    __tablename__ = "datasets"
    __table_args__ = (
        Index("idx_datasets_status_imported_at", "status", "imported_at"),
        Index("idx_datasets_sha256", "sha256"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(Text)
    canonical_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(20), default="upload")
    file_type: Mapped[str] = mapped_column(String(12))
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selected_sheet: Mapped[str | None] = mapped_column(String(255), nullable=True)
    available_sheets: Mapped[list[str]] = mapped_column(JSON, default=list)
    duplicate_columns: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="uploaded")
    frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    frequency_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    readiness_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    ready_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    columns: Mapped[list[DatasetColumn]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    mappings: Mapped[list[ColumnMapping]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    issues: Mapped[list[DataQualityIssue]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    report: Mapped[DataQualityReport | None] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", uselist=False
    )
    transformations: Mapped[list[DataTransformation]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    forecast_runs: Mapped[list[ForecastRun]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetColumn(Base):
    """Observed structure and sample statistics for one source column."""

    __tablename__ = "dataset_columns"
    __table_args__ = (Index("idx_dataset_columns_dataset_position", "dataset_id", "position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255))
    normalized_name: Mapped[str] = mapped_column(String(255))
    data_type: Mapped[str] = mapped_column(String(50))
    position: Mapped[int] = mapped_column(Integer)
    null_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_count: Mapped[int] = mapped_column(Integer, default=0)
    sample_values: Mapped[list[object]] = mapped_column(JSON, default=list)

    dataset: Mapped[Dataset] = relationship(back_populates="columns")


class ColumnMapping(Base):
    """The canonical role assigned to a source column."""

    __tablename__ = "column_mappings"
    __table_args__ = (
        Index("idx_column_mappings_dataset_role", "dataset_id", "role"),
        Index("idx_column_mappings_dataset_column", "dataset_id", "column_name", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    column_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(20), default="automatic")
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    dataset: Mapped[Dataset] = relationship(back_populates="mappings")


class DataQualityReport(Base):
    """One explainable readiness assessment for a dataset."""

    __tablename__ = "data_quality_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    observations: Mapped[int] = mapped_column(Integer, default=0)
    first_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frequency: Mapped[str] = mapped_column(String(20), default="irregular")
    frequency_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    sku_count: Mapped[int] = mapped_column(Integer, default=1)
    location_count: Mapped[int] = mapped_column(Integer, default=1)
    mapped_variable_count: Mapped[int] = mapped_column(Integer, default=0)
    readiness_score: Mapped[int] = mapped_column(Integer, default=0)
    component_scores: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    deductions: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    summary: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    has_critical_errors: Mapped[bool] = mapped_column(Boolean, default=False)

    dataset: Mapped[Dataset] = relationship(back_populates="report")


class DataQualityIssue(Base):
    """A non-mutating data quality finding."""

    __tablename__ = "data_quality_issues"
    __table_args__ = (Index("idx_quality_issues_dataset_severity", "dataset_id", "severity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    report_id: Mapped[int] = mapped_column(
        ForeignKey("data_quality_reports.id", ondelete="CASCADE"), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(10))
    code: Mapped[str] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(Text)
    column_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    count: Mapped[int] = mapped_column(Integer, default=1)
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)

    dataset: Mapped[Dataset] = relationship(back_populates="issues")


class DataTransformation(Base):
    """Auditable lineage record for a technical or future value transformation."""

    __tablename__ = "data_transformations"
    __table_args__ = (Index("idx_transformations_dataset_created", "dataset_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    column_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    row_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    transformed_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    method: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    dataset: Mapped[Dataset] = relationship(back_populates="transformations")


class ForecastRun(Base):
    """One reproducible forecast comparison for a canonical series."""

    __tablename__ = "forecast_runs"
    __table_args__ = (
        Index("idx_forecast_runs_dataset_created", "dataset_id", "created_at"),
        Index("idx_forecast_runs_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    frequency: Mapped[str] = mapped_column(String(20))
    requested_horizon: Mapped[int] = mapped_column(Integer)
    validation_horizon: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    data_cutoff: Mapped[datetime] = mapped_column(UTCDateTime())
    preprocessing_summary: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    seasonality_candidate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seasonality_evidence: Mapped[str] = mapped_column(String(20), default="insufficient")
    status: Mapped[str] = mapped_column(String(20), default="running")
    champion_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    champion_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)

    dataset: Mapped[Dataset] = relationship(back_populates="forecast_runs")
    model_results: Mapped[list[ForecastModelResult]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    points: Mapped[list[ForecastPoint]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class ForecastModelResult(Base):
    """Eligibility, parameters, metrics, and rank for one candidate model."""

    __tablename__ = "forecast_model_results"
    __table_args__ = (Index("idx_forecast_models_run_rank", "run_id", "rank"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(50))
    eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    parameters: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    stability: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    run: Mapped[ForecastRun] = relationship(back_populates="model_results")
    folds: Mapped[list[ForecastFoldResult]] = relationship(
        back_populates="model_result", cascade="all, delete-orphan"
    )


class ForecastFoldResult(Base):
    """One expanding-window out-of-sample evaluation fold."""

    __tablename__ = "forecast_fold_results"
    __table_args__ = (Index("idx_forecast_folds_model_index", "model_result_id", "fold_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_result_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_model_results.id", ondelete="CASCADE"), nullable=False
    )
    fold_index: Mapped[int] = mapped_column(Integer)
    train_start: Mapped[datetime] = mapped_column(UTCDateTime())
    train_end: Mapped[datetime] = mapped_column(UTCDateTime())
    validation_start: Mapped[datetime] = mapped_column(UTCDateTime())
    validation_end: Mapped[datetime] = mapped_column(UTCDateTime())
    training_observations: Mapped[int] = mapped_column(Integer)
    validation_observations: Mapped[int] = mapped_column(Integer)
    metrics: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    actual_values: Mapped[list[float | None]] = mapped_column(JSON, default=list)
    forecast_values: Mapped[list[float | None]] = mapped_column(JSON, default=list)

    model_result: Mapped[ForecastModelResult] = relationship(back_populates="folds")


class ForecastPoint(Base):
    """One future point with optional empirical uncertainty bounds."""

    __tablename__ = "forecast_points"
    __table_args__ = (Index("idx_forecast_points_run_timestamp", "run_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime())
    forecast: Mapped[float] = mapped_column(Float)
    lower_80: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_80: Mapped[float | None] = mapped_column(Float, nullable=True)
    lower_95: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_95: Mapped[float | None] = mapped_column(Float, nullable=True)

    run: Mapped[ForecastRun] = relationship(back_populates="points")
