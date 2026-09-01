"""Typed contracts for Inventory & Replenishment Engine."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, root_validator, validator

InputStatus = Literal["available", "missing", "not_applicable"]


class InventoryValueInput(BaseModel):
    value: float | None = None
    status: InputStatus = "missing"
    unit: str | None = Field(None, max_length=30)
    source_type: str = Field("manual", max_length=40)
    source_reference: str | None = Field(None, max_length=300)
    available_at: datetime | None = None

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
    def validate_value(cls, values: dict[str, object]) -> dict[str, object]:
        status, value = values.get("status"), values.get("value")
        if status == "available" and value is None:
            raise ValueError("available inputs require a value")
        if status != "available" and value is not None:
            raise ValueError("missing/not_applicable inputs cannot carry a value")
        if isinstance(value, (int, float)) and value < 0:
            raise ValueError("inventory inputs cannot be negative")
        return values


class InventoryOperationalInputs(BaseModel):
    inventory_on_hand: InventoryValueInput = Field(default_factory=InventoryValueInput)
    inventory_in_transit: InventoryValueInput = Field(default_factory=InventoryValueInput)
    safety_stock: InventoryValueInput = Field(default_factory=InventoryValueInput)
    lead_time: InventoryValueInput = Field(default_factory=InventoryValueInput)
    service_level: InventoryValueInput = Field(default_factory=InventoryValueInput)
    unit_cost: InventoryValueInput = Field(default_factory=InventoryValueInput)
    order_cost: InventoryValueInput = Field(default_factory=InventoryValueInput)
    holding_cost: InventoryValueInput = Field(default_factory=InventoryValueInput)
    holding_rate: InventoryValueInput = Field(default_factory=InventoryValueInput)
    moq: InventoryValueInput = Field(default_factory=InventoryValueInput)
    lot_multiple: InventoryValueInput = Field(default_factory=InventoryValueInput)
    capacity: InventoryValueInput = Field(default_factory=InventoryValueInput)
    committed_inventory: InventoryValueInput = Field(default_factory=InventoryValueInput)
    backorders: InventoryValueInput = Field(default_factory=InventoryValueInput)

    @validator("service_level")
    def validate_service_level(cls, item: InventoryValueInput) -> InventoryValueInput:
        if item.value is not None and not 0 < item.value <= 1:
            raise ValueError("service_level must be expressed as a proportion in (0, 1]")
        return item

    @validator("holding_rate")
    def validate_holding_rate(cls, item: InventoryValueInput) -> InventoryValueInput:
        if item.value is not None and not 0 < item.value <= 1:
            raise ValueError("holding_rate must be expressed as a proportion in (0, 1]")
        return item


class InventoryRequest(BaseModel):
    forecast_run_id: str
    scenario_run_id: str | None = None
    portfolio_run_id: str | None = None
    decision_run_id: str | None = None
    cutoff: datetime
    operational_inputs: InventoryOperationalInputs = Field(
        default_factory=InventoryOperationalInputs
    )
    include_in_transit: bool = False

    @validator("cutoff", pre=True)
    def normalize_cutoff(cls, value: datetime | str) -> datetime:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @validator("forecast_run_id", "scenario_run_id", "portfolio_run_id", "decision_run_id")
    def validate_uuid(cls, value: str | None) -> str | None:
        return str(UUID(value)) if value else None


class InventoryPreflightResponse(BaseModel):
    forecast_run_id: str
    dataset_id: str
    scenario_run_id: str | None = None
    portfolio_run_id: str | None = None
    decision_run_id: str | None = None
    cutoff: datetime
    product: str | None = None
    location: str | None = None
    category: str | None = None
    frequency: str
    horizon: int
    champion: str
    demand_source: str
    available_inputs: list[str]
    missing_inputs: list[str]
    calculable: dict[str, bool]
    readiness: Literal["ready", "warning", "blocked"]
    warnings: list[str]


class InventoryItemResponse(BaseModel):
    id: str
    forecast_run_id: str | None = None
    product: str | None = None
    location: str | None = None
    category: str | None = None
    frequency: str
    horizon: int
    demand_source: str
    forecast_total: float
    forecast_average: float
    inventory_on_hand: float | None = None
    inventory_in_transit: float | None = None
    safety_stock: float | None = None
    safety_stock_source: str | None = None
    lead_time: float | None = None
    lead_time_unit: str | None = None
    service_level: float | None = None
    unit_cost: float | None = None
    order_cost: float | None = None
    holding_cost: float | None = None
    moq: float | None = None
    capacity: float | None = None
    physical_coverage: float | None = None
    coverage_with_transit: float | None = None
    lead_time_demand: float | None = None
    reorder_point: float | None = None
    eoq: float | None = None
    projected_inventory: float | None = None
    projected_shortage: float | None = None
    projected_surplus: float | None = None
    raw_requirement: float | None = None
    recommended_quantity: float | None = None
    risk_level: str
    completeness: float
    inputs: dict[str, object]
    calculations: dict[str, object]
    constraints: list[dict[str, object]]
    missing_inputs: list[str]
    warnings: list[str]
    explanation: dict[str, object]
    evidence: dict[str, object]


class InventoryRunSummary(BaseModel):
    id: str
    dataset_id: str | None = None
    forecast_run_id: str | None = None
    scenario_run_id: str | None = None
    source_mode: str
    cutoff: datetime
    created_at: datetime
    available_at: datetime
    calculation_version: str
    status: str
    summary: dict[str, object]


class InventoryRunResponse(InventoryRunSummary):
    portfolio_run_id: str | None = None
    decision_run_id: str | None = None
    source_snapshot: dict[str, object]
    assumptions: dict[str, object]
    missing_inputs: list[str]
    scope: dict[str, object]
    coverage: dict[str, object]
    warnings: list[str]
    provenance: dict[str, object]
    items: list[InventoryItemResponse]


class InventoryDefinitionsResponse(BaseModel):
    calculation_version: str
    formulas: dict[str, str]
    service_levels: dict[str, float]
    compatible_time_units: dict[str, str]
    risk_rules: list[str]
    boundaries: list[str]
