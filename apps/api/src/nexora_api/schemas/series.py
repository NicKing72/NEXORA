"""REST contracts for canonical demand-series exploration."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

SeriesRequestFrequency = Literal["auto", "original", "daily", "weekly", "monthly"]
TrendClassification = Literal[
    "stable",
    "increasing_slight",
    "decreasing_slight",
    "increasing_moderate",
    "decreasing_moderate",
    "increasing_strong",
    "decreasing_strong",
]
EvidenceLevel = Literal["high", "moderate", "low", "insufficient"]


class ReadyDatasetSummary(BaseModel):
    id: str
    name: str
    source_type: str
    row_count: int
    readiness_score: int
    frequency: str
    ready_at: datetime | None


class DimensionValue(BaseModel):
    value: str
    observations: int


class ProductDimension(DimensionValue):
    categories: list[str] = Field(default_factory=list)


class SeriesDimensionsResponse(BaseModel):
    dataset_id: str
    products: list[ProductDimension] = Field(default_factory=list)
    locations: list[DimensionValue] = Field(default_factory=list)
    categories: list[DimensionValue] = Field(default_factory=list)
    first_date: date | None
    last_date: date | None
    source_frequency: str
    available_frequencies: list[SeriesRequestFrequency]


class SeriesSelection(BaseModel):
    dataset_id: str
    dataset_name: str
    product: str | None
    location: str | None
    category: str | None
    requested_frequency: SeriesRequestFrequency
    resolved_frequency: str
    start_date: date | None
    end_date: date | None
    data_cutoff: date
    is_aggregated: bool
    aggregation_note: str | None
    price_method: str | None


class EventCounts(BaseModel):
    missing: int = 0
    zero: int = 0
    outlier: int = 0
    stockout: int = 0


class SeriesPoint(BaseModel):
    date: str
    demand: float | None
    price: float | None = None
    stock: float | None = None
    promotion: bool | None = None
    expected_source_periods: int
    observed_source_periods: int
    coverage_ratio: float
    is_partial: bool
    events: EventCounts = Field(default_factory=EventCounts)


class ResultSeriesStatistics(BaseModel):
    periods: int
    valid_periods: int
    complete_periods: int
    partial_periods: int
    analyzed_periods: int
    first_date: str | None
    last_date: str | None
    total_demand: float | None
    mean_demand: float | None
    median_demand: float | None
    minimum_demand: float | None
    maximum_demand: float | None
    standard_deviation: float | None
    coefficient_of_variation: float | None
    completely_missing_periods: int
    zero_demand_periods: int
    analysis_excludes_partial_periods: bool
    total_includes_partial_periods: bool


class UnderlyingQualityStatistics(BaseModel):
    source_observations: int
    missing_demand_values: int
    zero_demand_observations: int
    outlier_observations: int
    possible_stockout_observations: int
    affected_periods: EventCounts


class SeriesStatistics(BaseModel):
    series: ResultSeriesStatistics
    underlying_quality: UnderlyingQualityStatistics


class PatternSummary(BaseModel):
    trend: TrendClassification
    slope_per_period: float
    approximate_change_percent: float | None
    volatility: Literal["low", "moderate", "high"]
    stability: Literal["stable", "variable", "insufficient"]
    intermittent: bool
    zero_percentage: float
    adi: float | None
    analyzed_periods: int
    excluded_partial_periods: int
    signals: list[str] = Field(default_factory=list)


class SeasonalityAdvice(BaseModel):
    candidate_label: str | None
    candidate_period: int | None
    evidence: EvidenceLevel
    autocorrelation: float | None
    paired_observations: int
    complete_cycles: int
    analyzed_periods: int
    excluded_partial_periods: int
    conclusion: Literal["potential", "inconclusive", "insufficient"]


class HoltWintersEligibility(BaseModel):
    compatible: bool
    candidate_period: int | None
    total_periods: int
    eligible_periods: int
    required_observations: int | None
    complete_cycles: int
    missing_values: int
    excluded_partial_periods: int
    seasonal_evidence: EvidenceLevel
    recommendation: Literal["favorable", "limited", "not_available"]
    reason_code: str


class SeriesProfileResponse(BaseModel):
    selection: SeriesSelection
    points: list[SeriesPoint]
    statistics: SeriesStatistics
    pattern: PatternSummary
    seasonality: SeasonalityAdvice
    holt_winters: HoltWintersEligibility
