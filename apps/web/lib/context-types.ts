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
  impact_status: "not_estimated";
  created_at: string;
  updated_at: string;
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
