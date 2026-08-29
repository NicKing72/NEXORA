import { apiRequest } from "@/lib/api-client";
import type { ForecastPreflight, ForecastRequest, ForecastRun } from "@/lib/forecast-types";

export function getForecastPreflight(
  request: ForecastRequest,
  signal?: AbortSignal,
): Promise<ForecastPreflight> {
  return apiRequest("/api/v1/forecast-runs/preflight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });
}

export function createForecastRun(request: ForecastRequest): Promise<ForecastRun> {
  return apiRequest("/api/v1/forecast-runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function getForecastRun(runId: string, signal?: AbortSignal): Promise<ForecastRun> {
  return apiRequest(`/api/v1/forecast-runs/${runId}`, { signal });
}
