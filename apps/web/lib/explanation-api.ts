import { apiRequest } from "@/lib/api-client";
import type {
  ExplanationPreflight,
  ExplanationRequest,
  ExplanationRun,
  ExplanationRunSummary,
  ForecastRunSummary,
} from "@/lib/explanation-types";

export function getExplanationForecasts(signal?: AbortSignal): Promise<ForecastRunSummary[]> {
  return apiRequest("/api/v1/forecast-runs", { signal });
}

export function getExplanationPreflight(
  request: ExplanationRequest,
  signal?: AbortSignal,
): Promise<ExplanationPreflight> {
  return apiRequest("/api/v1/explanations/preflight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });
}

export function createExplanation(request: ExplanationRequest): Promise<ExplanationRun> {
  return apiRequest("/api/v1/explanations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function getExplanations(signal?: AbortSignal): Promise<ExplanationRunSummary[]> {
  return apiRequest("/api/v1/explanations", { signal });
}

export function getExplanation(runId: string, signal?: AbortSignal): Promise<ExplanationRun> {
  return apiRequest(`/api/v1/explanations/${runId}`, { signal });
}
