"""Typed contracts for the auditable Explanation Engine."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ExplanationRequest(BaseModel):
    forecast_run_id: str
    cutoff: datetime | None = None
    scenario_run_id: str | None = None
    scor_assessment_id: str | None = None
    portfolio_run_id: str | None = None
    decision_run_id: str | None = None

    @validator(
        "forecast_run_id",
        "scenario_run_id",
        "scor_assessment_id",
        "portfolio_run_id",
        "decision_run_id",
    )
    def validate_uuid(cls, value: str | None) -> str | None:
        return str(UUID(value)) if value is not None else None

    @validator("cutoff")
    def normalize_cutoff(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class ModelDefinitionResponse(BaseModel):
    key: str
    name: str
    family: str
    formula: str
    patterns: list[str]
    inputs: list[str]
    strengths: list[str]
    limitations: list[str]


class ExplanationPreflightResponse(BaseModel):
    forecast_run_id: str
    dataset_id: str
    cutoff: datetime
    scope: dict[str, object]
    champion: dict[str, object]
    available_layers: dict[str, object]
    limitations: list[str]
    warnings: list[str]


class ExplanationEvidenceResponse(BaseModel):
    id: int
    evidence_type: str
    source_type: str
    source_id: str | None = None
    label: str
    value: dict[str, object]
    metadata: dict[str, object]
    provenance: dict[str, object]
    created_at: datetime


class ExplanationRunSummary(BaseModel):
    id: str
    forecast_run_id: str
    dataset_id: str
    series_id: str
    frequency: str
    horizon: int
    champion_model: str
    cutoff: datetime
    version: str
    status: str
    created_from: str
    created_at: datetime


class ExplanationRunResponse(ExplanationRunSummary):
    available_at: datetime
    source_snapshot: dict[str, object]
    limitations: list[str]
    evidence: list[ExplanationEvidenceResponse] = Field(default_factory=list)


class ExplanationModelsResponse(BaseModel):
    champion: dict[str, object]
    comparison: list[dict[str, object]]


class ExplanationBacktestingResponse(BaseModel):
    champion_model: str
    folds: list[dict[str, object]]
    summary: dict[str, object]


class ExplanationForecastResponse(BaseModel):
    summary: dict[str, object]
    points: list[dict[str, object]]


class ExplanationProvenanceResponse(BaseModel):
    sources: dict[str, object]
    limitations: list[str]
