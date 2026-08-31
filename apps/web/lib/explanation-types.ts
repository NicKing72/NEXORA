export type ExplanationRequest = {
  forecast_run_id: string;
  cutoff?: string;
  scenario_run_id?: string | null;
  scor_assessment_id?: string | null;
  portfolio_run_id?: string | null;
  decision_run_id?: string | null;
};

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

export type ExplanationModel = {
  id: number;
  model_name: string;
  status: string;
  eligible: boolean;
  rank: number | null;
  selection_score: number | null;
  metrics: Record<string, number | null>;
  stability: Record<string, string | number | null>;
  parameters: Record<string, string | number | boolean | null>;
  valid_folds: number;
  observations: number | null;
  is_champion: boolean;
  within_champion_tolerance: boolean;
  failure_reason: string | null;
  explanation: ModelExplanation;
};

export type ExplanationFold = {
  fold_index: number;
  train_start: string;
  train_end: string;
  validation_start: string;
  validation_end: string;
  training_observations: number;
  validation_observations: number;
  metrics: Record<string, number | null>;
};

export type ExplanationPoint = {
  timestamp: string;
  forecast: number;
  lower_80: number | null;
  upper_80: number | null;
  width_80: number | null;
  lower_95: number | null;
  upper_95: number | null;
  width_95: number | null;
};

export type ModelExplanation = {
  key: string;
  name: string;
  family: string;
  formula: string;
  patterns: string[];
  inputs: string[];
  strengths: string[];
  limitations: string[];
  parameters: Record<string, string | number | boolean | null>;
  parameters_available: boolean;
  engine: string | null;
  parameter_source: string | null;
};

export type ExplanationSnapshot = {
  scope: {
    dataset_id: string;
    dataset_name: string;
    series_id: string;
    product: string | null;
    location: string | null;
    category: string | null;
    frequency: string;
    horizon: number;
  };
  dataset: Record<string, unknown>;
  forecast: {
    id: string;
    created_at: string;
    data_cutoff: string;
    training_cutoff: string | null;
    frequency: string;
    horizon: number;
    validation_horizon: number;
    seasonality_candidate: number | null;
    seasonality_evidence: string;
    preprocessing: Record<string, unknown>;
    warnings: string[];
    calculation_version: string | null;
  };
  champion: {
    model_name: string;
    reason: string | null;
    rank: number | null;
    metrics: Record<string, number | null>;
    stability: Record<string, string | number | null>;
    explanation: ModelExplanation;
  };
  comparison: ExplanationModel[];
  backtesting: {
    champion_model: string;
    folds: ExplanationFold[];
    summary: Record<string, unknown>;
  };
  forecast_output: {
    summary: Record<string, unknown> & {
      start: string | null;
      end: string | null;
      total: number | null;
      average: number | null;
      minimum: number | null;
      maximum: number | null;
      trend: { label: string; relative_change: number | null; rule: string };
      has_80_interval: boolean;
      has_95_interval: boolean;
      average_width_80: number | null;
      average_width_95: number | null;
    };
    points: ExplanationPoint[];
  };
  layers: Record<string, Record<string, unknown> | null>;
  provenance: Record<string, unknown>;
};

export type ExplanationEvidence = {
  id: number;
  evidence_type: string;
  source_type: string;
  source_id: string | null;
  label: string;
  value: Record<string, unknown>;
  metadata: Record<string, unknown>;
  provenance: Record<string, unknown>;
  created_at: string;
};

export type ExplanationRunSummary = {
  id: string;
  forecast_run_id: string;
  dataset_id: string;
  series_id: string;
  frequency: string;
  horizon: number;
  champion_model: string;
  cutoff: string;
  version: string;
  status: string;
  created_from: string;
  created_at: string;
};

export type ExplanationRun = ExplanationRunSummary & {
  available_at: string;
  source_snapshot: ExplanationSnapshot;
  limitations: string[];
  evidence: ExplanationEvidence[];
};

export type ExplanationPreflight = {
  forecast_run_id: string;
  dataset_id: string;
  cutoff: string;
  scope: ExplanationSnapshot["scope"];
  champion: ExplanationSnapshot["champion"];
  available_layers: Record<string, boolean>;
  limitations: string[];
  warnings: string[];
};
