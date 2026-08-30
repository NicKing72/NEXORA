import type { FutureForecastPoint } from "@/lib/forecast-types";

export type ForecastRunSummary = {
  id: string;
  dataset_id: string;
  frequency: string;
  requested_horizon: number;
  created_at: string;
  data_cutoff: string;
  status: string;
  champion_model: string | null;
};

export type ContextImpactOption = {
  estimate_id: string;
  signal_id: string;
  title: string;
  signal_type: string;
  relative_delta: number;
  evidence_score: number;
  evidence_level: string;
  event_periods: number;
  reference_periods: number;
  baseline_value: number | null;
  method: string;
};

export type ScenarioPreflight = {
  forecast_run_id: string;
  dataset_id: string;
  selection: Record<string, string | null>;
  frequency: string;
  horizon: number;
  champion_model: string;
  data_cutoff: string;
  baseline_points: FutureForecastPoint[];
  eligible_context_impacts: ContextImpactOption[];
  warnings: string[];
};

export type AssumptionKind =
  | "demand_percent"
  | "demand_absolute"
  | "promotion"
  | "price_change"
  | "stock_restriction"
  | "context_impact"
  | "custom";

export type ScenarioAssumptionDraft = {
  clientId: string;
  assumption_type: AssumptionKind;
  label: string;
  start_at: string;
  end_at: string;
  magnitude: number;
  context_signal_id?: string;
  context_impact_estimate_id?: string;
};

export type ScenarioAssumption = {
  id: string;
  order_index: number;
  assumption_type: AssumptionKind;
  label: string;
  start_at: string;
  end_at: string | null;
  scope: Record<string, unknown>;
  magnitude: number | null;
  unit: string;
  application_method: string;
  source_type: "user_hypothesis" | "historical_evidence";
  context_signal_id: string | null;
  context_impact_estimate_id: string | null;
  provenance: Record<string, unknown>;
  warnings: string[];
};

export type ScenarioPoint = {
  timestamp: string;
  baseline: number;
  scenario: number;
  absolute_delta: number;
  relative_delta: number | null;
  lower_80: number | null;
  upper_80: number | null;
  lower_95: number | null;
  upper_95: number | null;
  active_assumption_ids: string[];
};

export type ScenarioRunSummary = {
  id: string;
  forecast_run_id: string;
  dataset_id: string;
  name: string;
  status: string;
  frequency: string;
  horizon: number;
  champion_model: string;
  created_at: string;
  executed_at: string | null;
  total_relative_delta: number | null;
};

export type ScenarioRun = ScenarioRunSummary & {
  description: string;
  data_cutoff: string;
  selection: Record<string, string | null>;
  baseline_snapshot: Record<string, unknown>;
  provenance: Record<string, unknown>;
  summary: {
    baseline_total?: number;
    scenario_total?: number;
    absolute_delta?: number;
    relative_delta?: number | null;
    max_period_change?: number;
    affected_periods?: number;
    assumption_count?: number;
  };
  warnings: string[];
  assumptions: ScenarioAssumption[];
  points: ScenarioPoint[];
  audit: Array<Record<string, unknown>>;
};
