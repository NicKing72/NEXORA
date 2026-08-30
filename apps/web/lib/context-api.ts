import { apiRequest } from "@/lib/api-client";
import type { ContextFilters, ContextSignal, ManualSignalInput, RelevantSignal } from "@/lib/context-types";

function filterParameters(filters: ContextFilters): URLSearchParams {
  const parameters = new URLSearchParams();
  if (filters.datasetId) parameters.set("dataset_id", filters.datasetId);
  if (filters.product) parameters.set("product", filters.product);
  if (filters.location) parameters.set("location", filters.location);
  if (filters.category) parameters.set("category", filters.category);
  if (filters.family) parameters.set("signal_family", filters.family);
  if (filters.status) parameters.set("status", filters.status);
  if (filters.source) parameters.set("source_type", filters.source);
  if (filters.eventFrom) parameters.set("event_from", new Date(`${filters.eventFrom}T00:00:00`).toISOString());
  if (filters.eventTo) parameters.set("event_to", new Date(`${filters.eventTo}T23:59:59`).toISOString());
  if (filters.cutoff) parameters.set("cutoff", new Date(filters.cutoff).toISOString());
  return parameters;
}

export function getContextSignals(filters: ContextFilters, signal?: AbortSignal): Promise<ContextSignal[]> {
  return apiRequest(`/api/v1/context-signals?${filterParameters(filters).toString()}`, { signal });
}

export function getRelevantSignals(filters: ContextFilters, signal?: AbortSignal): Promise<RelevantSignal[]> {
  const parameters = filterParameters(filters);
  parameters.delete("signal_family");
  parameters.delete("status");
  parameters.delete("source_type");
  return apiRequest(`/api/v1/context-signals/relevant?${parameters.toString()}`, { signal });
}

export function createContextSignal(payload: ManualSignalInput): Promise<ContextSignal> {
  return apiRequest("/api/v1/context-signals", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateContextSignalStatus(id: string, status: string): Promise<ContextSignal> {
  return apiRequest(`/api/v1/context-signals/${id}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}

export function regenerateDemoContext(datasetId: string): Promise<{ generated: number; signals: ContextSignal[] }> {
  return apiRequest("/api/v1/context-signals/demo/regenerate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_id: datasetId }),
  });
}
