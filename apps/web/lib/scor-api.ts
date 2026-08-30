import { apiRequest } from "@/lib/api-client";
import type {
  ScorAssessment,
  ScorAssessmentSummary,
  ScorBenchmarkProfile,
  ScorDefinition,
  ScorMetricInputDraft,
} from "@/lib/scor-types";

export const listScorDefinitions = (): Promise<ScorDefinition[]> => apiRequest("/api/v1/scor/definitions");
export const listScorAssessments = (): Promise<ScorAssessmentSummary[]> => apiRequest("/api/v1/scor/assessments");
export const getScorAssessment = (id: string): Promise<ScorAssessment> => apiRequest(`/api/v1/scor/assessments/${id}`);
export const listScorProfiles = (): Promise<ScorBenchmarkProfile[]> => apiRequest("/api/v1/scor/benchmark-profiles");

export function regenerateScorDemo(): Promise<{ assessment: ScorAssessment; benchmark_profile: ScorBenchmarkProfile }> {
  return apiRequest("/api/v1/scor/demo/regenerate", { method: "POST" });
}

export function calculateScorAssessment(id: string): Promise<ScorAssessment> {
  return apiRequest(`/api/v1/scor/assessments/${id}/calculate`, { method: "POST" });
}

export function applyScorBenchmark(id: string, profileId: string): Promise<ScorAssessment> {
  return apiRequest(`/api/v1/scor/assessments/${id}/benchmark`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ benchmark_profile_id: profileId }),
  });
}

export function createScorAssessment(input: {
  name: string;
  companyName: string;
  periodStart: string;
  periodEnd: string;
  cutoff: string;
  sourceName: string;
  metricInputs: ScorMetricInputDraft[];
}): Promise<ScorAssessment> {
  return apiRequest("/api/v1/scor/assessments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: input.name,
      company_name: input.companyName || null,
      period_start: new Date(`${input.periodStart}T00:00:00`).toISOString(),
      period_end: new Date(`${input.periodEnd}T23:59:59`).toISOString(),
      cutoff: new Date(input.cutoff).toISOString(),
      source_name: input.sourceName,
      source_metadata: { entry_method: "manual_aggregated_raw_inputs" },
      metric_inputs: input.metricInputs.map((item) => ({
        ...item,
        available_at: new Date(item.available_at).toISOString(),
        source: input.sourceName,
        provenance: { entry_method: "manual" },
      })),
    }),
  });
}
