export type ScorProcess = "PLAN" | "SOURCE" | "MAKE" | "DELIVER" | "RETURN";

export type ScorDefinition = {
  id: string;
  process: ScorProcess;
  process_label: string;
  attribute: string;
  display_name: string;
  formula: string;
  inputs: Array<{
    id: string;
    label: string;
    required: boolean;
    nonnegative: boolean;
    direct_percentage: boolean;
  }>;
  unit: string;
  method: string;
  desired_direction: string;
  version: string;
};

export type ScorMetricResult = {
  id: number;
  metric_id: string;
  process: ScorProcess;
  process_label: string;
  attribute: string;
  display_name: string;
  method: string;
  formula: string;
  substituted_formula: string;
  inputs: Record<string, unknown>;
  numerator: number | null;
  denominator: number | null;
  result_value: number | null;
  ratio_decimal: number | null;
  unit: string;
  evidence_status: "complete" | "incomplete" | "insufficient_evidence" | "invalid" | "not_applicable";
  reason: string | null;
  calculation_details: Record<string, unknown>;
  target: Record<string, unknown>;
  gap_score: number | null;
  calculated_at: string;
  algorithm_version: string;
};

export type ScorProcessResult = {
  id: number;
  process: ScorProcess;
  metrics_total: number;
  metrics_complete: number;
  metrics_insufficient: number;
  metrics_not_applicable: number;
  metrics_evaluable: number;
  data_coverage: number;
  benchmark_coverage: number;
  weighted_gap_score: number | null;
  confidence: string;
  rank: number | null;
  details: { contributors?: Array<Record<string, unknown>> };
};

export type ScorAssessmentSummary = {
  id: string;
  name: string;
  company_name: string | null;
  period_start: string;
  period_end: string;
  cutoff: string;
  status: string;
  source_name: string;
  benchmark_profile_id: string | null;
  forecast_run_id: string | null;
  metric_count: number;
  created_at: string;
  calculated_at: string | null;
};

export type ScorAssessment = ScorAssessmentSummary & {
  source_dataset_id: string | null;
  source_metadata: Record<string, unknown>;
  summary: Record<string, number>;
  criticality: Record<string, unknown>;
  warnings: string[];
  algorithm_version: string;
  metric_inputs: Array<Record<string, unknown>>;
  metrics: ScorMetricResult[];
  processes: ScorProcessResult[];
  audit: Array<Record<string, unknown>>;
};

export type ScorBenchmarkProfile = {
  id: string;
  name: string;
  profile_type: string;
  active: boolean;
  source: string;
  notes: string;
  is_official_scor: false;
  minimum_process_coverage: number;
  targets: Array<Record<string, unknown>>;
  created_at: string;
};

export type ScorMetricInputDraft = {
  metric_id: string;
  values: Record<string, number>;
  metadata: Record<string, string>;
  not_applicable: boolean;
  available_at: string;
};
