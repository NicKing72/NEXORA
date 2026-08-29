"""REST contracts for Data Studio datasets, mappings, previews, and quality."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, validator

from nexora_api.services.data_studio.constants import CANONICAL_ROLES, NON_EXCLUSIVE_ROLES


class OrmModel(BaseModel):
    class Config:
        orm_mode = True


class DatasetColumnResponse(OrmModel):
    name: str
    normalized_name: str
    data_type: str
    position: int
    null_count: int
    unique_count: int
    sample_values: list[Any]


class ColumnMappingResponse(OrmModel):
    column_name: str
    role: str
    confidence: float
    source: str
    updated_at: datetime


class DatasetResponse(OrmModel):
    id: str
    original_filename: str
    source_type: str
    file_type: str
    mime_type: str | None
    file_size: int
    sha256: str
    row_count: int | None
    column_count: int | None
    selected_sheet: str | None
    available_sheets: list[str]
    duplicate_columns: list[str]
    status: str
    frequency: str | None
    frequency_confidence: float | None
    readiness_score: int | None
    imported_at: datetime
    ready_at: datetime | None
    columns: list[DatasetColumnResponse] = []
    mappings: list[ColumnMappingResponse] = []


class SheetListResponse(BaseModel):
    dataset_id: str
    selected_sheet: str | None
    sheets: list[str]


class SheetSelection(BaseModel):
    sheet: str = Field(min_length=1, max_length=255)


class DatasetPreviewResponse(BaseModel):
    dataset_id: str
    columns: list[str]
    rows: list[dict[str, Any]]
    total_rows: int


class MappingUpdateItem(BaseModel):
    column_name: str = Field(min_length=1, max_length=255)
    role: str

    @validator("role")
    def validate_role(cls, value: str) -> str:
        valid = set(CANONICAL_ROLES) | set(NON_EXCLUSIVE_ROLES)
        if value not in valid:
            raise ValueError("Unsupported canonical role")
        return value


class MappingUpdateRequest(BaseModel):
    mappings: list[MappingUpdateItem] = Field(min_items=1)


class QualityIssueResponse(OrmModel):
    id: int
    severity: Literal["ERROR", "WARNING", "INFO"]
    code: str
    message: str
    column_name: str | None
    count: int
    details: dict[str, Any]


class QualityReportResponse(OrmModel):
    id: int
    dataset_id: str
    created_at: datetime
    observations: int
    first_date: datetime | None
    last_date: datetime | None
    duration_days: int | None
    frequency: str
    frequency_confidence: float
    sku_count: int
    location_count: int
    mapped_variable_count: int
    readiness_score: int
    component_scores: dict[str, int]
    deductions: list[dict[str, Any]]
    summary: dict[str, Any]
    has_critical_errors: bool


class QualityAssessmentResponse(BaseModel):
    report: QualityReportResponse
    issues: list[QualityIssueResponse]


class ReadyResponse(BaseModel):
    dataset: DatasetResponse
    report: QualityReportResponse
    issues: list[QualityIssueResponse]
