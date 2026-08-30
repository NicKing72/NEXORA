export type SignalFamily =
  | "commercial"
  | "competitor"
  | "calendar"
  | "weather"
  | "market"
  | "digital"
  | "operations"
  | "supply_chain"
  | "event"
  | "news"
  | "macro"
  | "custom";

export type KnowledgeType = "observed" | "known_future" | "forecasted_external" | "scenario";
export type SignalStatus = "detected" | "reviewed" | "confirmed" | "dismissed" | "expired";
export type SourceType = "manual" | "company_data" | "api" | "web" | "system";
export type ScopeType = "global" | "country" | "region" | "location" | "category" | "product" | "channel" | "market" | "custom";
export type ImpactStatus = "not_estimated" | "estimated" | "insufficient_evidence" | "not_observable" | "not_applicable" | "pending";
export type EvidenceLevel = "insufficient" | "low" | "moderate" | "high";

export type ContextSignal = {
  id: string;
  dataset_id: string | null;
  signal_family: SignalFamily;
  signal_type: string;
  title: string;
  description: string;
  event_start: string;
  event_end: string | null;
  observed_at: string | null;
  available_at: string;
  status: SignalStatus;
  source_type: SourceType;
  source_name: string;
  source_reference: string | null;
  confidence: number | null;
  intensity: number | null;
  knowledge_type: KnowledgeType;
  scope_type: ScopeType;
  country: string | null;
  region: string | null;
  product: string | null;
  category: string | null;
  location: string | null;
  channel: string | null;
  market: string | null;
  metadata: Record<string, unknown>;
  impact_status: ImpactStatus;
  created_at: string;
  updated_at: string;
};

export type ContextImpactEstimate = {
  id: string;
  signal_id: string;
  dataset_id: string;
  scope: Record<string, unknown>;
  frequency: string;
  method: string;
  status: Exclude<ImpactStatus, "not_estimated">;
  direction: "increase" | "decrease" | "neutral" | "unknown";
  baseline_value: number | null;
  observed_value: number | null;
  absolute_delta: number | null;
  relative_delta: number | null;
  sample_size: number;
  event_periods: number;
  reference_periods: number;
  evidence_score: number;
  evidence_level: EvidenceLevel;
  data_cutoff: string;
  availability_cutoff: string;
  estimated_at: string;
  reason_code: string | null;
  notes: string | null;
  evidence_breakdown: {
    formula_version?: string;
    components?: Record<string, number>;
  };
  quality_summary: Record<string, number | boolean>;
  input_snapshot: Record<string, unknown>;
};

export type ContextAnalogy = {
  signal_id: string;
  status: "available" | "insufficient_evidence" | "not_applicable";
  comparable_events: number;
  minimum_relative_delta: number | null;
  median_relative_delta: number | null;
  maximum_relative_delta: number | null;
  estimate_ids: string[];
  reason_code: string | null;
  notes: string;
};

export type RelevanceReason = { dimension: string; expected: string; actual: string };
export type RelevantSignal = { signal: ContextSignal; match_reasons: RelevanceReason[] };

export type ContextFilters = {
  datasetId: string;
  product: string;
  location: string;
  category: string;
  family: string;
  status: string;
  source: string;
  eventFrom: string;
  eventTo: string;
  cutoff: string;
};

export type ManualSignalInput = {
  dataset_id: string | null;
  signal_family: SignalFamily;
  signal_type: string;
  title: string;
  description: string;
  event_start: string;
  event_end: string | null;
  observed_at: string | null;
  available_at: string;
  knowledge_type: KnowledgeType;
  scope_type: ScopeType;
  product: string | null;
  category: string | null;
  location: string | null;
  confidence: number | null;
  source_reference: string | null;
  metadata: Record<string, unknown>;
};
