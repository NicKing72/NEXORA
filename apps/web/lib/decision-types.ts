import type { ForecastRunSummary } from "@/lib/scenario-types";

export type { ForecastRunSummary };

export type DecisionPreflight = {
  forecast_run_id: string;
  dataset_id: string;
  selection: Record<string, string | null>;
  champion: {
    model_name: string;
    reason: string | null;
    metrics: Record<string, number | null>;
    stability: Record<string, string | number | null>;
    fold_count: number;
  };
  forecast_summary: {
    point_count: number;
    first_value: number;
    last_value: number;
    total: number;
    trajectory_delta: number | null;
    mean_relative_interval_width_95: number | null;
    first_period: string;
    last_period: string;
    points: Array<{
      timestamp: string;
      forecast: number;
      lower_80: number | null;
      upper_80: number | null;
      lower_95: number | null;
      upper_95: number | null;
    }>;
  };
  decision_cutoff: string;
  scenarios: Array<{
    id: string;
    name: string;
    relative_delta: number | null;
    affected_periods: number;
    warnings: string[];
    created_at: string;
    hypothetical: true;
  }>;
  relevant_context: Array<Record<string, unknown>>;
  usable_impacts: Array<Record<string, unknown>>;
  missing_operational_inputs: string[];
  warnings: string[];
};

export type DecisionEvidence = {
  id: number;
  evidence_type: string;
  source_id: string | null;
  description: string;
  snapshot: Record<string, unknown>;
  created_at: string;
};

export type DecisionStatus =
  | "open"
  | "acknowledged"
  | "under_review"
  | "dismissed"
  | "resolved";

export type DecisionRecommendation = {
  id: string;
  decision_run_id: string;
  rank: number;
  priority: "low" | "medium" | "high" | "critical";
  action_type: string;
  title: string;
  summary: string;
  rationale: string;
  support_score: number;
  evidence_level: string;
  scope: Record<string, string | null>;
  dataset_id: string;
  product: string | null;
  location: string | null;
  category: string | null;
  forecast_run_id: string;
  scenario_run_id: string | null;
  context_signal_ids: string[];
  context_impact_ids: string[];
  decision_cutoff: string;
  status: DecisionStatus;
  limitations: string[];
  provenance: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  evidence: DecisionEvidence[];
  audit: Array<Record<string, unknown>>;
};

export type DecisionRunSummary = {
  id: string;
  forecast_run_id: string;
  scenario_run_id: string | null;
  dataset_id: string;
  decision_cutoff: string;
  status: string;
  recommendation_count: number;
  high_priority_count: number;
  created_at: string;
};

export type DecisionRun = DecisionRunSummary & {
  source_snapshot: {
    selection: Record<string, string | null>;
    champion: Record<string, unknown>;
    forecast_summary: DecisionPreflight["forecast_summary"];
    signals: Array<Record<string, unknown>>;
    impacts: Record<string, Record<string, unknown>>;
    analogies: Record<string, Record<string, unknown>>;
    scenario: null | {
      id: string;
      name: string;
      summary: Record<string, number | null>;
      warnings: string[];
      assumptions: Array<Record<string, unknown>>;
      points: Array<{
        timestamp: string;
        baseline: number;
        scenario: number;
        absolute_delta: number;
        relative_delta: number | null;
        active_assumption_ids: string[];
      }>;
      hypothetical: true;
      official_forecast_modified: false;
    };
    missing_operational_inputs: string[];
    immutable_sources: true;
    causal_inference: false;
  };
  summary: {
    recommendation_count: number;
    priority_counts: Record<string, number>;
    high_priority_count: number;
    requires_review_count: number;
    scenario_considered: boolean;
    context_signal_count: number;
    context_impact_count: number;
  };
  warnings: string[];
  recommendations: DecisionRecommendation[];
};
