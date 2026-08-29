export type SeriesRequestFrequency = "auto" | "original" | "daily" | "weekly" | "monthly";

export type ReadyDatasetSummary = {
  id: string;
  name: string;
  source_type: string;
  row_count: number;
  readiness_score: number;
  frequency: string;
  ready_at: string | null;
};

export type DimensionValue = { value: string; observations: number };
export type ProductDimension = DimensionValue & { categories: string[] };

export type SeriesDimensions = {
  dataset_id: string;
  products: ProductDimension[];
  locations: DimensionValue[];
  categories: DimensionValue[];
  first_date: string | null;
  last_date: string | null;
  source_frequency: string;
  available_frequencies: SeriesRequestFrequency[];
};

export type EventCounts = {
  missing: number;
  zero: number;
  outlier: number;
  stockout: number;
};

export type SeriesPoint = {
  date: string;
  demand: number | null;
  price: number | null;
  stock: number | null;
  promotion: boolean | null;
  expected_source_periods: number;
  observed_source_periods: number;
  coverage_ratio: number;
  is_partial: boolean;
  events: EventCounts;
};

export type ResultSeriesStatistics = {
  periods: number;
  valid_periods: number;
  complete_periods: number;
  partial_periods: number;
  analyzed_periods: number;
  first_date: string | null;
  last_date: string | null;
  total_demand: number | null;
  mean_demand: number | null;
  median_demand: number | null;
  minimum_demand: number | null;
  maximum_demand: number | null;
  standard_deviation: number | null;
  coefficient_of_variation: number | null;
  completely_missing_periods: number;
  zero_demand_periods: number;
  analysis_excludes_partial_periods: boolean;
  total_includes_partial_periods: boolean;
};

export type UnderlyingQualityStatistics = {
  source_observations: number;
  missing_demand_values: number;
  zero_demand_observations: number;
  outlier_observations: number;
  possible_stockout_observations: number;
  affected_periods: EventCounts;
};

export type SeriesStatistics = {
  series: ResultSeriesStatistics;
  underlying_quality: UnderlyingQualityStatistics;
};

export type PatternSummary = {
  trend:
    | "stable"
    | "increasing_slight"
    | "decreasing_slight"
    | "increasing_moderate"
    | "decreasing_moderate"
    | "increasing_strong"
    | "decreasing_strong";
  slope_per_period: number;
  approximate_change_percent: number | null;
  volatility: "low" | "moderate" | "high";
  stability: "stable" | "variable" | "insufficient";
  intermittent: boolean;
  zero_percentage: number;
  adi: number | null;
  analyzed_periods: number;
  excluded_partial_periods: number;
  signals: string[];
};

export type SeasonalityAdvice = {
  candidate_label: string | null;
  candidate_period: number | null;
  evidence: "high" | "moderate" | "low" | "insufficient";
  autocorrelation: number | null;
  paired_observations: number;
  complete_cycles: number;
  analyzed_periods: number;
  excluded_partial_periods: number;
  conclusion: "potential" | "inconclusive" | "insufficient";
};

export type HoltWintersEligibility = {
  compatible: boolean;
  candidate_period: number | null;
  total_periods: number;
  eligible_periods: number;
  required_observations: number | null;
  complete_cycles: number;
  missing_values: number;
  excluded_partial_periods: number;
  seasonal_evidence: "high" | "moderate" | "low" | "insufficient";
  recommendation: "favorable" | "limited" | "not_available";
  reason_code: string;
};

export type SeriesProfile = {
  selection: {
    dataset_id: string;
    dataset_name: string;
    product: string | null;
    location: string | null;
    category: string | null;
    requested_frequency: SeriesRequestFrequency;
    resolved_frequency: string;
    start_date: string | null;
    end_date: string | null;
    data_cutoff: string;
    is_aggregated: boolean;
    aggregation_note: string | null;
    price_method: string | null;
  };
  points: SeriesPoint[];
  statistics: SeriesStatistics;
  pattern: PatternSummary;
  seasonality: SeasonalityAdvice;
  holt_winters: HoltWintersEligibility;
};

export type SeriesFilters = {
  datasetId: string;
  product: string;
  location: string;
  category: string;
  frequency: SeriesRequestFrequency;
  startDate: string;
  endDate: string;
};
