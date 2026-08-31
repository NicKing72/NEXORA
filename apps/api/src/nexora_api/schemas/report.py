"""Typed API contracts for immutable auditable reports."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, validator

ReportType = Literal["integrated", "forecast", "decisions", "scor", "portfolio"]


class ReportRequest(BaseModel):
    report_type: ReportType
    title: str = Field(min_length=3, max_length=180)
    report_cutoff: datetime
    forecast_run_id: str | None = None
    scenario_run_id: str | None = None
    scor_assessment_id: str | None = None
    portfolio_run_id: str | None = None
    decision_run_id: str | None = None
    explanation_run_id: str | None = None

    @validator(
        "forecast_run_id",
        "scenario_run_id",
        "scor_assessment_id",
        "portfolio_run_id",
        "decision_run_id",
        "explanation_run_id",
    )
    def validate_uuid(cls, value: str | None) -> str | None:
        return str(UUID(value)) if value is not None else None

    @validator("report_cutoff")
    def normalize_cutoff(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class ReportDefinitionResponse(BaseModel):
    calculation_version: str
    report_types: list[dict[str, object]]
    source_layers: list[str]
    export_formats: list[str]
    boundaries: list[str]


class ReportPreflightResponse(BaseModel):
    report_type: str
    report_cutoff: datetime
    dataset_id: str | None = None
    scope: dict[str, object]
    sources: dict[str, object]
    coverage: dict[str, object]
    warnings: list[str]
    limitations: list[str]
    ready: bool


class ReportSectionResponse(BaseModel):
    id: int
    section_type: str
    position: int
    payload: dict[str, object]
    source_references: list[dict[str, object]]
    completeness: str
    created_at: datetime


class ReportRunSummary(BaseModel):
    id: str
    report_type: str
    title: str
    status: str
    report_cutoff: datetime
    created_at: datetime
    calculation_version: str
    is_demo: bool
    dataset_id: str | None = None
    forecast_run_id: str | None = None
    scenario_run_id: str | None = None
    scor_assessment_id: str | None = None
    portfolio_run_id: str | None = None
    decision_run_id: str | None = None
    explanation_run_id: str | None = None
    layer_count: int
    coverage: dict[str, object]
    warning_count: int
    scope: dict[str, object]


class ReportRunResponse(ReportRunSummary):
    available_at: datetime
    source_snapshot: dict[str, object]
    report_payload: dict[str, object]
    warnings: list[str]
    limitations: list[str]
    sections: list[ReportSectionResponse] = Field(default_factory=list)


class ReportSourcesResponse(BaseModel):
    report_run_id: str
    sources: dict[str, object]
    provenance: dict[str, object]


class ReportSummaryResponse(BaseModel):
    report_run_id: str
    executive_summary: dict[str, object]
    coverage: dict[str, object]
    warnings: list[str]
    limitations: list[str]
