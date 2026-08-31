export type ReportType = "integrated" | "forecast" | "decisions" | "scor" | "portfolio";

export type ReportRequest = {
  report_type: ReportType;
  title: string;
  report_cutoff: string;
  forecast_run_id: string | null;
  scenario_run_id: string | null;
  scor_assessment_id: string | null;
  portfolio_run_id: string | null;
  decision_run_id: string | null;
  explanation_run_id: string | null;
};

export type ReportCoverage = {
  included: number;
  total: number;
  ratio: number;
  status: "complete" | "partial" | "insufficient";
  included_layers: string[];
  missing_layers: string[];
  meaning: string;
};

export type ReportPreflight = {
  report_type: ReportType;
  report_cutoff: string;
  dataset_id: string | null;
  scope: Record<string, unknown>;
  sources: Record<string, { included: boolean; id: string | null }>;
  coverage: ReportCoverage;
  warnings: string[];
  limitations: string[];
  ready: boolean;
};

export type ReportSection = {
  id: number;
  section_type: string;
  position: number;
  payload: Record<string, unknown>;
  source_references: Array<Record<string, unknown>>;
  completeness: string;
  created_at: string;
};

export type ReportRunSummary = {
  id: string;
  report_type: ReportType;
  title: string;
  status: string;
  report_cutoff: string;
  created_at: string;
  calculation_version: string;
  is_demo: boolean;
  dataset_id: string | null;
  forecast_run_id: string | null;
  scenario_run_id: string | null;
  scor_assessment_id: string | null;
  portfolio_run_id: string | null;
  decision_run_id: string | null;
  explanation_run_id: string | null;
  layer_count: number;
  coverage: ReportCoverage;
  warning_count: number;
  scope: Record<string, unknown>;
};

export type ReportRun = ReportRunSummary & {
  available_at: string;
  source_snapshot: Record<string, Record<string, unknown> | null>;
  report_payload: {
    executive_summary: {
      facts: string[];
      recommendations: Array<string | null>;
      uncertainties: string[];
      missing_data: string[];
      limitations: string[];
      causal_claims: boolean;
      generated_deterministically: boolean;
    };
    coverage: ReportCoverage;
    scope: Record<string, unknown>;
    section_count: number;
    snapshot_immutable: boolean;
    sources_recalculated: boolean;
  };
  warnings: string[];
  limitations: string[];
  sections: ReportSection[];
};

export type ReportDefinitions = {
  calculation_version: string;
  report_types: Array<{ key: ReportType; label: string; required: string[] }>;
  source_layers: string[];
  export_formats: string[];
  boundaries: string[];
};

export type SourceSummary = {
  id: string;
  forecast_run_id?: string | null;
  dataset_id?: string | null;
  source_dataset_id?: string | null;
  scenario_run_id?: string | null;
  scor_assessment_id?: string | null;
  portfolio_run_id?: string | null;
  forecast_run_ids?: string[];
  status?: string;
  name?: string;
  title?: string;
  champion_model?: string | null;
  frequency?: string;
  created_at?: string;
  calculated_at?: string | null;
};
