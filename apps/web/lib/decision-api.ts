import { apiRequest } from "@/lib/api-client";
import type {
  DecisionPreflight,
  DecisionRun,
  DecisionRunSummary,
  DecisionStatus,
  ForecastRunSummary,
} from "@/lib/decision-types";

export function listDecisionForecasts(): Promise<ForecastRunSummary[]> {
  return apiRequest("/api/v1/forecast-runs");
}

export function getDecisionPreflight(input: {
  forecastRunId: string;
  scenarioRunId?: string | null;
  scorAssessmentId?: string | null;
  portfolioRunId?: string | null;
  decisionCutoff?: string | null;
}): Promise<DecisionPreflight> {
  return apiRequest("/api/v1/decisions/preflight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      forecast_run_id: input.forecastRunId,
      scenario_run_id: input.scenarioRunId || null,
      scor_assessment_id: input.scorAssessmentId || null,
      portfolio_run_id: input.portfolioRunId || null,
      decision_cutoff: input.decisionCutoff || null,
    }),
  });
}

export function createDecisionRun(input: {
  forecastRunId: string;
  scenarioRunId?: string | null;
  scorAssessmentId?: string | null;
  portfolioRunId?: string | null;
  decisionCutoff?: string | null;
}): Promise<DecisionRun> {
  return apiRequest("/api/v1/decisions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      forecast_run_id: input.forecastRunId,
      scenario_run_id: input.scenarioRunId || null,
      scor_assessment_id: input.scorAssessmentId || null,
      portfolio_run_id: input.portfolioRunId || null,
      decision_cutoff: input.decisionCutoff || null,
    }),
  });
}

export function listDecisionRuns(): Promise<DecisionRunSummary[]> {
  return apiRequest("/api/v1/decisions");
}

export function getDecisionRun(runId: string): Promise<DecisionRun> {
  return apiRequest(`/api/v1/decisions/${runId}`);
}

export function updateDecisionStatus(
  recommendationId: string,
  status: DecisionStatus,
): Promise<DecisionRun["recommendations"][number]> {
  return apiRequest(`/api/v1/decisions/recommendations/${recommendationId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}
