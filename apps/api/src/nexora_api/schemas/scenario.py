"""REST contracts for conditional, non-official scenario simulations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, root_validator, validator

AssumptionType = Literal[
    "demand_percent",
    "demand_absolute",
    "promotion",
    "price_change",
    "stock_restriction",
    "context_impact",
    "custom",
]
AssumptionUnit = Literal["ratio", "absolute", "capacity_ratio"]
ApplicationMethod = Literal["multiplicative", "additive", "sales_capacity_cap"]
SourceType = Literal["user_hypothesis", "historical_evidence"]


class ScenarioAssumptionInput(BaseModel):
    assumption_type: AssumptionType
    label: str = Field(..., min_length=2, max_length=160)
    start_at: datetime
    end_at: datetime | None = None
    scope: dict[str, object] = Field(default_factory=dict)
    magnitude: float | None = Field(None, ge=-10_000_000, le=10_000_000)
    unit: AssumptionUnit
    application_method: ApplicationMethod
    source_type: SourceType = "user_hypothesis"
    context_signal_id: str | None = None
    context_impact_estimate_id: str | None = None
    source_note: str | None = Field(None, max_length=1000)

    @validator("start_at", "end_at", pre=True)
    def normalize_instant(cls, value: datetime | str | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, str) and len(value) == 10:
            value = datetime.fromisoformat(value)
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @validator("context_signal_id", "context_impact_estimate_id")
    def validate_optional_uuid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(UUID(value))

    @root_validator(skip_on_failure=True)
    def validate_contract(cls, values: dict[str, object]) -> dict[str, object]:
        start = values.get("start_at")
        end = values.get("end_at")
        if isinstance(start, datetime) and isinstance(end, datetime) and end < start:
            raise ValueError("end_at must be on or after start_at")
        if values.get("magnitude") is None:
            raise ValueError("magnitude is required")
        kind = values.get("assumption_type")
        unit = values.get("unit")
        method = values.get("application_method")
        expected = {
            "demand_absolute": ("absolute", "additive"),
            "stock_restriction": ("capacity_ratio", "sales_capacity_cap"),
        }
        expected_unit, expected_method = expected.get(str(kind), ("ratio", "multiplicative"))
        if unit != expected_unit or method != expected_method:
            raise ValueError(f"{kind} requires {expected_unit}/{expected_method}")
        magnitude = float(values["magnitude"])
        if unit == "capacity_ratio" and not 0 <= magnitude <= 1:
            raise ValueError("stock capacity ratio must be between 0 and 1")
        if method == "multiplicative" and magnitude < -1:
            raise ValueError("a relative assumption cannot reduce demand below zero")
        if kind == "context_impact" and (
            not values.get("context_signal_id") or not values.get("context_impact_estimate_id")
        ):
            raise ValueError("context impact assumptions require signal and estimate IDs")
        return values


class ScenarioCreateRequest(BaseModel):
    forecast_run_id: str
    name: str = Field(..., min_length=2, max_length=160)
    description: str = Field("", max_length=2000)
    frequency: str | None = Field(None, max_length=20)
    assumptions: list[ScenarioAssumptionInput] = Field(..., min_items=1, max_items=20)

    @validator("forecast_run_id")
    def validate_run_uuid(cls, value: str) -> str:
        return str(UUID(value))


class ScenarioPreflightRequest(BaseModel):
    forecast_run_id: str

    @validator("forecast_run_id")
    def validate_run_uuid(cls, value: str) -> str:
        return str(UUID(value))


class ScenarioAssumptionResponse(BaseModel):
    id: str
    order_index: int
    assumption_type: str
    label: str
    start_at: datetime
    end_at: datetime | None = None
    scope: dict[str, object]
    magnitude: float | None = None
    unit: str
    application_method: str
    source_type: str
    context_signal_id: str | None = None
    context_impact_estimate_id: str | None = None
    provenance: dict[str, object]
    warnings: list[str]


class ScenarioPointResponse(BaseModel):
    timestamp: str
    baseline: float
    scenario: float
    absolute_delta: float
    relative_delta: float | None = None
    lower_80: float | None = None
    upper_80: float | None = None
    lower_95: float | None = None
    upper_95: float | None = None
    active_assumption_ids: list[str]


class ScenarioRunSummary(BaseModel):
    id: str
    forecast_run_id: str
    dataset_id: str
    name: str
    status: str
    frequency: str
    horizon: int
    champion_model: str
    created_at: datetime
    executed_at: datetime | None = None
    total_relative_delta: float | None = None


class ScenarioRunResponse(ScenarioRunSummary):
    description: str
    data_cutoff: str
    selection: dict[str, object]
    baseline_snapshot: dict[str, object]
    provenance: dict[str, object]
    summary: dict[str, object]
    warnings: list[str]
    assumptions: list[ScenarioAssumptionResponse]
    points: list[ScenarioPointResponse]
    audit: list[dict[str, object]]


class ScenarioPreflightResponse(BaseModel):
    forecast_run_id: str
    dataset_id: str
    selection: dict[str, object]
    frequency: str
    horizon: int
    champion_model: str
    data_cutoff: str
    baseline_points: list[dict[str, object]]
    eligible_context_impacts: list[dict[str, object]]
    warnings: list[str]
