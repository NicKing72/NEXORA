"""Pydantic contracts for Forecast Core v1."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from nexora_api.schemas.series import SeriesPoint, SeriesRequestFrequency, SeriesSelection


class ForecastRunRequest(BaseModel):
    dataset_id: str = Field(min_length=36, max_length=36)
    product: str | None = Field(None, max_length=255)
    location: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=255)
    frequency: SeriesRequestFrequency = "auto"
    horizon: int | None = Field(None, ge=1, le=365)


class ModelEligibilitySummary(BaseModel):
    model_name: str
    eligible: bool
    reason: str | None = None
    final_fit_eligible: bool
    final_fit_reason: str | None = None
    backtest_evaluable: bool
    backtest_reason: str | None = None
    evaluable_folds: int
    total_folds: int


class ForecastPreflightResponse(BaseModel):
    selection: SeriesSelection
    horizon: int
    data_cutoff: str
    training_cutoff: str
    preprocessing: dict[str, object]
    interpolation_audit: list[dict[str, object]]
    warnings: list[str]
    seasonality: dict[str, object]
    holt_winters: dict[str, object]
    quality: dict[str, object]
    model_eligibility: list[ModelEligibilitySummary]


class ForecastFoldResponse(BaseModel):
    id: int
    fold_index: int
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    training_observations: int
    validation_observations: int
    metrics: dict[str, object]
    actual_values: list[float | None]
    forecast_values: list[float | None]


class ForecastModelResponse(BaseModel):
    id: int
    model_name: str
    eligible: bool
    final_fit_eligible: bool
    backtest_evaluable: bool
    backtest_reason: str | None = None
    status: Literal["pending", "not_eligible", "not_evaluable", "failed", "succeeded"]
    failure_reason: str | None = None
    parameters: dict[str, object]
    metrics: dict[str, object]
    stability: dict[str, object]
    rank: int | None = None
    folds: list[ForecastFoldResponse] = Field(default_factory=list)


class ForecastPointResponse(BaseModel):
    timestamp: str
    forecast: float
    lower_80: float | None = None
    upper_80: float | None = None
    lower_95: float | None = None
    upper_95: float | None = None


class ForecastRunResponse(BaseModel):
    id: str
    dataset_id: str
    selection: SeriesSelection
    frequency: str
    requested_horizon: int
    validation_horizon: int
    created_at: datetime
    data_cutoff: str
    training_cutoff: str
    preprocessing: dict[str, object]
    seasonality_candidate: int | None = None
    seasonality_evidence: str
    status: Literal["running", "completed", "failed"]
    champion_model: str | None = None
    champion_reason: str | None = None
    warnings: list[str]
    history: list[SeriesPoint]
    models: list[ForecastModelResponse]
    forecast_points: list[ForecastPointResponse]


class ForecastRunSummary(BaseModel):
    id: str
    dataset_id: str
    frequency: str
    requested_horizon: int
    created_at: datetime
    data_cutoff: str
    status: str
    champion_model: str | None = None
