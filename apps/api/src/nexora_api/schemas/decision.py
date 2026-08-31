"""Typed REST contracts for deterministic decision support."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, validator

DecisionPriority = Literal["low", "medium", "high", "critical"]
DecisionStatus = Literal["open", "acknowledged", "under_review", "dismissed", "resolved"]


class DecisionRequest(BaseModel):
    forecast_run_id: str
    scenario_run_id: str | None = None
    scor_assessment_id: str | None = None
    decision_cutoff: datetime | None = None

    @validator("forecast_run_id", "scenario_run_id", "scor_assessment_id")
    def validate_uuid(cls, value: str | None) -> str | None:
        return str(UUID(value)) if value is not None else None

    @validator("decision_cutoff")
    def normalize_cutoff(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class DecisionStatusUpdate(BaseModel):
    status: DecisionStatus
    note: str | None = Field(None, max_length=1000)


class DecisionEvidenceResponse(BaseModel):
    id: int
    evidence_type: str
    source_id: str | None = None
    description: str
    snapshot: dict[str, object]
    created_at: datetime


class DecisionRecommendationResponse(BaseModel):
    id: str
    decision_run_id: str
    rank: int
    priority: DecisionPriority
    action_type: str
    title: str
    summary: str
    rationale: str
    support_score: float
    evidence_level: str
    scope: dict[str, object]
    dataset_id: str
    product: str | None = None
    location: str | None = None
    category: str | None = None
    forecast_run_id: str
    scenario_run_id: str | None = None
    context_signal_ids: list[str]
    context_impact_ids: list[str]
    scor_assessment_id: str | None = None
    scor_support_contribution: float = 0
    scor_origin: str | None = None
    decision_cutoff: datetime
    status: DecisionStatus
    limitations: list[str]
    provenance: dict[str, object]
    created_at: datetime
    updated_at: datetime
    evidence: list[DecisionEvidenceResponse] = Field(default_factory=list)
    audit: list[dict[str, object]] = Field(default_factory=list)


class DecisionRunSummary(BaseModel):
    id: str
    forecast_run_id: str
    scenario_run_id: str | None = None
    scor_assessment_id: str | None = None
    dataset_id: str
    decision_cutoff: datetime
    status: str
    recommendation_count: int
    high_priority_count: int
    created_at: datetime


class DecisionRunResponse(DecisionRunSummary):
    source_snapshot: dict[str, object]
    summary: dict[str, object]
    warnings: list[str]
    recommendations: list[DecisionRecommendationResponse]


class DecisionPreflightResponse(BaseModel):
    forecast_run_id: str
    dataset_id: str
    selection: dict[str, object]
    champion: dict[str, object]
    forecast_summary: dict[str, object]
    decision_cutoff: datetime
    scenarios: list[dict[str, object]]
    relevant_context: list[dict[str, object]]
    usable_impacts: list[dict[str, object]]
    scor_assessments: list[dict[str, object]]
    selected_scor: dict[str, object] | None = None
    missing_operational_inputs: list[str]
    warnings: list[str]


class DecisionComparisonResponse(BaseModel):
    forecast_run_id: str
    scenario_run_id: str | None = None
    baseline_total: float
    scenario_total: float | None = None
    absolute_delta: float | None = None
    relative_delta: float | None = None
    affected_periods: int
    scenario_is_hypothetical: bool
    official_forecast_modified: bool
