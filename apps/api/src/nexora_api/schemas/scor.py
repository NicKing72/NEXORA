"""Typed REST contracts for SCOR diagnostics."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, validator


class ScorDefinitionInputResponse(BaseModel):
    id: str
    label: str
    required: bool
    nonnegative: bool
    direct_percentage: bool


class ScorDefinitionResponse(BaseModel):
    id: str
    process: str
    process_label: str
    attribute: str
    display_name: str
    formula: str
    inputs: list[ScorDefinitionInputResponse]
    unit: str
    method: str
    desired_direction: str
    source_type: str
    version: str


class ScorMetricInputPayload(BaseModel):
    metric_id: str = Field(..., min_length=3, max_length=10)
    values: dict[str, object] = Field(default_factory=dict)
    monthly_values: list[dict[str, object]] = Field(default_factory=list, max_items=6)
    metadata: dict[str, object] = Field(default_factory=dict)
    source: str = Field("manual", min_length=1, max_length=180)
    provenance: dict[str, object] = Field(default_factory=dict)
    not_applicable: bool = False
    available_at: datetime

    @validator("available_at")
    def normalize_available_at(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class ScorAssessmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=180)
    company_name: str | None = Field(None, max_length=180)
    source_dataset_id: str | None = None
    forecast_run_id: str | None = None
    benchmark_profile_id: str | None = None
    period_start: datetime
    period_end: datetime
    cutoff: datetime
    source_name: str = Field(..., min_length=1, max_length=180)
    source_metadata: dict[str, object] = Field(default_factory=dict)
    metric_inputs: list[ScorMetricInputPayload] = Field(default_factory=list)

    @validator("period_start", "period_end", "cutoff")
    def normalize_dates(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class ScorBenchmarkTargetCreate(BaseModel):
    metric_id: str
    direction: Literal["higher_is_better", "lower_is_better", "target_range"]
    target: float | None = None
    optional_min: float | None = None
    optional_max: float | None = None
    weight: float = Field(1.0, gt=0, le=100)
    source: str = Field(..., min_length=1, max_length=180)
    notes: str = Field("", max_length=1000)


class ScorBenchmarkProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=180)
    profile_type: Literal[
        "company_target", "contractual_sla", "historical_internal", "manually_defined", "demo"
    ]
    active: bool = True
    source: str = Field(..., min_length=1, max_length=180)
    notes: str = Field("", max_length=2000)
    minimum_process_coverage: float = Field(0.5, ge=0, le=1)
    targets: list[ScorBenchmarkTargetCreate]


class ScorBenchmarkApply(BaseModel):
    benchmark_profile_id: str


class ScorAssessmentSummary(BaseModel):
    id: str
    name: str
    company_name: str | None = None
    period_start: datetime
    period_end: datetime
    cutoff: datetime
    status: str
    source_name: str
    benchmark_profile_id: str | None = None
    forecast_run_id: str | None = None
    metric_count: int
    created_at: datetime
    calculated_at: datetime | None = None


class ScorMetricInputResponse(BaseModel):
    id: int
    metric_id: str
    values: dict[str, object]
    monthly_values: list[dict[str, object]]
    metadata: dict[str, object]
    source: str
    provenance: dict[str, object]
    not_applicable: bool
    available_at: datetime
    created_at: datetime


class ScorMetricResultResponse(BaseModel):
    id: int
    metric_id: str
    process: str
    process_label: str
    attribute: str
    display_name: str
    method: str
    formula: str
    substituted_formula: str
    inputs: dict[str, object]
    numerator: float | None
    denominator: float | None
    result_value: float | None
    ratio_decimal: float | None
    unit: str
    evidence_status: str
    reason: str | None
    calculation_details: dict[str, object]
    target: dict[str, object]
    gap_score: float | None
    calculated_at: datetime
    algorithm_version: str


class ScorProcessResultResponse(BaseModel):
    id: int
    process: str
    metrics_total: int
    metrics_complete: int
    metrics_insufficient: int
    metrics_not_applicable: int
    metrics_evaluable: int
    data_coverage: float
    benchmark_coverage: float
    weighted_gap_score: float | None
    confidence: str
    rank: int | None
    details: dict[str, object]


class ScorAuditResponse(BaseModel):
    id: int
    action: str
    details: dict[str, object]
    created_at: datetime


class ScorAssessmentResponse(ScorAssessmentSummary):
    source_dataset_id: str | None = None
    source_metadata: dict[str, object]
    summary: dict[str, object]
    criticality: dict[str, object]
    warnings: list[str]
    algorithm_version: str
    metric_inputs: list[ScorMetricInputResponse]
    metrics: list[ScorMetricResultResponse]
    processes: list[ScorProcessResultResponse]
    audit: list[ScorAuditResponse]


class ScorBenchmarkProfileResponse(BaseModel):
    id: str
    name: str
    profile_type: str
    active: bool
    source: str
    notes: str
    is_official_scor: bool
    minimum_process_coverage: float
    targets: list[dict[str, object]]
    created_at: datetime


class ScorDemoResponse(BaseModel):
    assessment: ScorAssessmentResponse
    benchmark_profile: ScorBenchmarkProfileResponse
