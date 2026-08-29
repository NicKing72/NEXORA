export type WorkflowStep = "import" | "map" | "validate" | "ready";
export type OperationState = "idle" | "dragging" | "uploading" | "processing" | "success" | "warning" | "error";

export type DatasetColumn = {
  name: string;
  normalized_name: string;
  data_type: string;
  position: number;
  null_count: number;
  unique_count: number;
  sample_values: unknown[];
};

export type ColumnMapping = {
  column_name: string;
  role: string;
  confidence: number;
  source: "automatic" | "confirmed" | "manual";
  updated_at: string;
};

export type Dataset = {
  id: string;
  original_filename: string;
  source_type: "upload" | "demo";
  file_type: "csv" | "xlsx" | "xls";
  mime_type: string | null;
  file_size: number;
  sha256: string;
  row_count: number | null;
  column_count: number | null;
  selected_sheet: string | null;
  available_sheets: string[];
  duplicate_columns: string[];
  status: string;
  frequency: string | null;
  frequency_confidence: number | null;
  readiness_score: number | null;
  imported_at: string;
  ready_at: string | null;
  columns: DatasetColumn[];
  mappings: ColumnMapping[];
};

export type DatasetPreview = {
  dataset_id: string;
  columns: string[];
  rows: Record<string, unknown>[];
  total_rows: number;
};

export type QualityIssue = {
  id: number;
  severity: "ERROR" | "WARNING" | "INFO";
  code: string;
  message: string;
  column_name: string | null;
  count: number;
  details: Record<string, unknown>;
};

export type QualityReport = {
  id: number;
  dataset_id: string;
  created_at: string;
  observations: number;
  first_date: string | null;
  last_date: string | null;
  duration_days: number | null;
  frequency: string;
  frequency_confidence: number;
  sku_count: number;
  location_count: number;
  mapped_variable_count: number;
  readiness_score: number;
  component_scores: Record<string, number>;
  deductions: Array<{ component: string; points_lost: number; component_score: number }>;
  summary: Record<string, unknown>;
  has_critical_errors: boolean;
};

export type QualityAssessment = {
  report: QualityReport;
  issues: QualityIssue[];
};

export type ReadyPayload = QualityAssessment & { dataset: Dataset };
