import type { SeriesPoint, SeriesRequestFrequency } from "@/lib/series-types";

export type ForecastRequest = {
  dataset_id: string;
  product: string | null;
  location: string | null;
  category: string | null;
  frequency: SeriesRequestFrequency;
  horizon: number;
};

export type MetricSet = {
  observations?: number;
  mae?: number | null;
  rmse?: number | null;
  mape?: number | null;
  smape?: number | null;
  wmape?: number | null;
  bias?: number | null;
  bias_percent?: number | null;
};

export type ForecastFold = {
  id: number;
  fold_index: number;
  train_start: string;
  train_end: string;
  validation_start: string;
  validation_end: string;
  training_observations: number;
  validation_observations: number;
  metrics: MetricSet;
  actual_values: Array<number | null>;
  forecast_values: Array<number | null>;
};

export type ForecastModelResult = {
  id: number;
  model_name: string;
  eligible: boolean;
  final_fit_eligible: boolean;
  backtest_evaluable: boolean;
  backtest_reason: string | null;
  status: "pending" | "not_eligible" | "not_evaluable" | "failed" | "succeeded";
  failure_reason: string | null;
  parameters: Record<string, string | number | boolean | null>;
  metrics: MetricSet;
  stability: { label?: "high" | "moderate" | "low" | "insufficient"; wmape_cv?: number | null };
  rank: number | null;
  folds: ForecastFold[];
};

export type FutureForecastPoint = {
  timestamp: string;
  forecast: number;
  lower_80: number | null;
  upper_80: number | null;
  lower_95: number | null;
  upper_95: number | null;
};

export type ForecastPreflight = {
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
  horizon: number;
  data_cutoff: string;
  training_cutoff: string;
  preprocessing: Record<string, unknown> & {
    source_periods: number;
    training_periods: number;
    valid_training_values: number;
    excluded_partial_periods: number;
    missing_before: number;
    interpolated_values: number;
    continuous_for_training: boolean;
    outliers_preserved: number;
    possible_stockouts_preserved: number;
    zero_values_preserved: number;
  };
  interpolation_audit: Array<Record<string, unknown>>;
  warnings: string[];
  seasonality: { candidate_period?: number | null; evidence?: string; candidate_label?: string | null };
  holt_winters: { compatible?: boolean; recommendation?: string };
  quality: Record<string, number | Record<string, number>>;
  model_eligibility: Array<{
    model_name: string;
    eligible: boolean;
    reason: string | null;
    final_fit_eligible: boolean;
    final_fit_reason: string | null;
    backtest_evaluable: boolean;
    backtest_reason: string | null;
    evaluable_folds: number;
    total_folds: number;
  }>;
};

export type ForecastRun = {
  id: string;
  dataset_id: string;
  selection: ForecastPreflight["selection"];
  frequency: string;
  requested_horizon: number;
  validation_horizon: number;
  created_at: string;
  data_cutoff: string;
  training_cutoff: string;
  preprocessing: ForecastPreflight["preprocessing"] & {
    interval_method?: string;
    interval_residual_count?: number;
  };
  seasonality_candidate: number | null;
  seasonality_evidence: string;
  status: "running" | "completed" | "failed";
  champion_model: string | null;
  champion_reason: string | null;
  warnings: string[];
  history: SeriesPoint[];
  models: ForecastModelResult[];
  forecast_points: FutureForecastPoint[];
};
