"""Typed API contracts for the operational Portfolio Engine."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, root_validator, validator

InputStatus = Literal["available", "missing", "not_applicable"]


class OperationalValueInput(BaseModel):
    value: float | None = None
    status: InputStatus = "missing"
    available_at: datetime | None = None
    source_type: str = Field("manual", max_length=40)
    source_reference: str | None = Field(None, max_length=300)

    @validator("available_at", pre=True)
    def normalize_datetime(cls, value: datetime | str | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @root_validator(skip_on_failure=True)
    def validate_status_value(cls, values: dict[str, object]) -> dict[str, object]:
        status = values.get("status")
        value = values.get("value")
        if status == "available" and value is None:
            raise ValueError("available operational inputs require a value")
        if status != "available" and value is not None:
            raise ValueError("missing or not-applicable inputs cannot carry a value")
        if isinstance(value, (float, int)) and value < 0:
            raise ValueError("operational values cannot be negative")
        return values


class PortfolioOperationalInputs(BaseModel):
    current_inventory: OperationalValueInput = Field(default_factory=OperationalValueInput)
    inbound_inventory: OperationalValueInput = Field(default_factory=OperationalValueInput)
    safety_stock: OperationalValueInput = Field(default_factory=OperationalValueInput)
    lead_time: OperationalValueInput = Field(default_factory=OperationalValueInput)
    unit_cost: OperationalValueInput = Field(default_factory=OperationalValueInput)
    service_level: OperationalValueInput = Field(default_factory=OperationalValueInput)
    moq: OperationalValueInput = Field(default_factory=OperationalValueInput)
    capacity: OperationalValueInput = Field(default_factory=OperationalValueInput)


class PortfolioRequest(BaseModel):
    dataset_id: str | None = None
    forecast_run_ids: list[str] = Field(default_factory=list, max_items=500)
    cutoff: datetime
    filters: dict[str, str | None] = Field(default_factory=dict)
    operational_inputs: dict[str, PortfolioOperationalInputs] = Field(default_factory=dict)

    @validator("cutoff", pre=True)
    def normalize_cutoff(cls, value: datetime | str) -> datetime:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @validator("dataset_id")
    def validate_dataset_id(cls, value: str | None) -> str | None:
        return str(UUID(value)) if value else None

    @validator("forecast_run_ids")
    def validate_run_ids(cls, values: list[str]) -> list[str]:
        return [str(UUID(value)) for value in values]

    @root_validator(skip_on_failure=True)
    def require_scope(cls, values: dict[str, object]) -> dict[str, object]:
        if not values.get("dataset_id") and not values.get("forecast_run_ids"):
            raise ValueError("dataset_id or forecast_run_ids is required")
        return values


class PortfolioCandidateResponse(BaseModel):
    forecast_run_id: str
    dataset_id: str
    dataset_name: str
    product: str | None = None
    location: str | None = None
    category: str | None = None
    frequency: str
    horizon: int
    champion: str
    created_at: datetime
    data_cutoff: str


class PortfolioPreflightResponse(BaseModel):
    dataset_id: str
    cutoff: datetime
    forecast_runs_found: int
    series_compatible: int
    frequency: str | None = None
    horizon: int | None = None
    candidates: list[PortfolioCandidateResponse]
    operational_inputs_available: int
    missing_operational_inputs: list[str]
    valid_aggregations: list[str]
    invalid_aggregations: list[str]
    warnings: list[str]
    readiness: Literal["ready", "warning", "blocked"]


class PortfolioItemResponse(BaseModel):
    id: str
    rank: int
    series_key: str
    product: str | None = None
    location: str | None = None
    category: str | None = None
    family: str | None = None
    forecast_run_id: str | None = None
    champion: str
    forecast_horizon: int
    forecast_frequency: str
    forecast_total: float
    forecast_average: float
    forecast_peak: float
    forecast_minimum: float
    forecast_variability: float | None = None
    interval_information: dict[str, object]
    operational_inputs: dict[str, object]
    current_inventory: float | None = None
    inbound_inventory: float | None = None
    safety_stock: float | None = None
    lead_time: float | None = None
    inventory_coverage: float | None = None
    coverage_status: str
    projected_exposure: float | None = None
    operational_data_completeness: str
    risk_level: str
    priority_score: float
    score_status: str
    score_components: dict[str, object]
    priority_reasons: list[str]
    missing_inputs: list[str]
    warnings: list[str]
    provenance: dict[str, object]


class PortfolioRunSummary(BaseModel):
    id: str
    dataset_id: str | None = None
    source_mode: str
    cutoff: datetime
    created_at: datetime
    available_at: datetime
    calculation_version: str
    number_of_series: int
    summary: dict[str, object]


class PortfolioRunResponse(PortfolioRunSummary):
    forecast_run_ids: list[str]
    filters: dict[str, object]
    warnings: list[str]
    provenance: dict[str, object]
    items: list[PortfolioItemResponse]


class PortfolioDefinitionsResponse(BaseModel):
    calculation_version: str
    priority_formula: dict[str, object]
    risk_order: list[str]
    operational_fields: list[str]
    boundaries: list[str]
