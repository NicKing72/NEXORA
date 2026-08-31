import type { ForecastRunSummary } from "@/lib/scenario-types";

export type { ForecastRunSummary };

export type OperationalStatus = "available" | "missing" | "not_applicable";

export type OperationalValue = {
  value: number | null;
  status: OperationalStatus;
  available_at: string;
  source_type: string;
  source_reference: string | null;
};

export type PortfolioCandidate = {
  forecast_run_id: string;
  dataset_id: string;
  dataset_name: string;
  product: string | null;
  location: string | null;
  category: string | null;
  frequency: string;
  horizon: number;
  champion: string;
  created_at: string;
  data_cutoff: string;
};

export type PortfolioPreflight = {
  dataset_id: string;
  cutoff: string;
  forecast_runs_found: number;
  series_compatible: number;
  frequency: string | null;
  horizon: number | null;
  candidates: PortfolioCandidate[];
  operational_inputs_available: number;
  missing_operational_inputs: string[];
  valid_aggregations: string[];
  invalid_aggregations: string[];
  warnings: string[];
  readiness: "ready" | "warning" | "blocked";
};

export type PortfolioItem = {
  id: string;
  rank: number;
  series_key: string;
  product: string | null;
  location: string | null;
  category: string | null;
  family: string | null;
  forecast_run_id: string | null;
  champion: string;
  forecast_horizon: number;
  forecast_frequency: string;
  forecast_total: number;
  forecast_average: number;
  forecast_peak: number;
  forecast_minimum: number;
  forecast_variability: number | null;
  interval_information: Record<string, { periods?: number; average_width?: number | null }>;
  operational_inputs: Record<string, OperationalValue>;
  current_inventory: number | null;
  inbound_inventory: number | null;
  safety_stock: number | null;
  lead_time: number | null;
  inventory_coverage: number | null;
  coverage_status: string;
  projected_exposure: number | null;
  operational_data_completeness: "sufficient_data" | "partial_data" | "insufficient_data";
  risk_level: "critical" | "high" | "medium" | "low" | "unknown";
  priority_score: number;
  score_status: "complete" | "partial";
  score_components: Record<string, {
    available: boolean;
    raw_score: number | null;
    configured_weight: number;
    normalized_weight: number | null;
  }>;
  priority_reasons: string[];
  missing_inputs: string[];
  warnings: string[];
  provenance: Record<string, unknown>;
};

export type PortfolioSummary = {
  series_evaluated: number;
  risk_counts: Record<PortfolioItem["risk_level"], number>;
  completeness_counts: Record<PortfolioItem["operational_data_completeness"], number>;
  operational_information_coverage: number;
  forecast_aggregate_valid: boolean;
  forecast_total_aggregate: number | null;
  forecast_peak_relevant: number | null;
  coverage_evaluable_series: number;
};

export type PortfolioRunSummary = {
  id: string;
  dataset_id: string | null;
  source_mode: "official" | "demo";
  cutoff: string;
  created_at: string;
  available_at: string;
  calculation_version: string;
  number_of_series: number;
  summary: PortfolioSummary;
};

export type PortfolioRun = PortfolioRunSummary & {
  forecast_run_ids: string[];
  filters: Record<string, unknown>;
  warnings: string[];
  provenance: Record<string, unknown>;
  items: PortfolioItem[];
};

export type OperationalDraft = {
  current_inventory: string;
  inbound_inventory: string;
  safety_stock: string;
  lead_time: string;
};
