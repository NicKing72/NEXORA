"""REST contracts for deterministic contextual impact evidence."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

ImpactStatus = Literal[
    "estimated",
    "insufficient_evidence",
    "not_observable",
    "not_applicable",
    "pending",
]
ImpactDirection = Literal["increase", "decrease", "neutral", "unknown"]
ImpactEvidenceLevel = Literal["insufficient", "low", "moderate", "high"]
ImpactFrequency = Literal["auto", "original", "daily", "weekly", "monthly"]


class ContextImpactEstimateRequest(BaseModel):
    frequency: ImpactFrequency = "auto"
    data_cutoff: date | None = None
    availability_cutoff: datetime | None = None


class ContextImpactEstimateResponse(BaseModel):
    id: str
    signal_id: str
    dataset_id: str
    scope: dict[str, object] = Field(default_factory=dict)
    frequency: str
    method: str
    status: ImpactStatus
    direction: ImpactDirection
    baseline_value: float | None
    observed_value: float | None
    absolute_delta: float | None
    relative_delta: float | None
    sample_size: int
    event_periods: int
    reference_periods: int
    evidence_score: float
    evidence_level: ImpactEvidenceLevel
    data_cutoff: datetime
    availability_cutoff: datetime
    estimated_at: datetime
    reason_code: str | None
    notes: str | None
    evidence_breakdown: dict[str, object] = Field(default_factory=dict)
    quality_summary: dict[str, object] = Field(default_factory=dict)
    input_snapshot: dict[str, object] = Field(default_factory=dict)


class ContextImpactDatasetResponse(BaseModel):
    dataset_id: str
    estimates: list[ContextImpactEstimateResponse] = Field(default_factory=list)


class ContextAnalogyResponse(BaseModel):
    signal_id: str
    status: Literal["available", "insufficient_evidence", "not_applicable"]
    comparable_events: int
    minimum_relative_delta: float | None = None
    median_relative_delta: float | None = None
    maximum_relative_delta: float | None = None
    estimate_ids: list[str] = Field(default_factory=list)
    reason_code: str | None = None
    notes: str

