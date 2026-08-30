import { apiRequest } from "@/lib/api-client";
import type {
  ForecastRunSummary,
  ScenarioAssumptionDraft,
  ScenarioPreflight,
  ScenarioRun,
  ScenarioRunSummary,
} from "@/lib/scenario-types";

export function listForecastRuns(): Promise<ForecastRunSummary[]> {
  return apiRequest("/api/v1/forecast-runs");
}

export function getScenarioPreflight(forecastRunId: string): Promise<ScenarioPreflight> {
  return apiRequest("/api/v1/scenarios/preflight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ forecast_run_id: forecastRunId }),
  });
}

export function listScenarios(): Promise<ScenarioRunSummary[]> {
  return apiRequest("/api/v1/scenarios");
}

export function getScenario(scenarioId: string): Promise<ScenarioRun> {
  return apiRequest(`/api/v1/scenarios/${scenarioId}`);
}

export function createScenario(input: {
  forecastRunId: string;
  name: string;
  description: string;
  frequency: string;
  scope: Record<string, string>;
  assumptions: ScenarioAssumptionDraft[];
}): Promise<ScenarioRun> {
  return apiRequest("/api/v1/scenarios", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      forecast_run_id: input.forecastRunId,
      name: input.name,
      description: input.description,
      frequency: input.frequency,
      assumptions: input.assumptions.map((item) => {
        const isAbsolute = item.assumption_type === "demand_absolute";
        const isStock = item.assumption_type === "stock_restriction";
        const isContext = item.assumption_type === "context_impact";
        return {
          assumption_type: item.assumption_type,
          label: item.label,
          start_at: item.start_at,
          end_at: item.end_at || null,
          scope: input.scope,
          magnitude: item.magnitude,
          unit: isStock ? "capacity_ratio" : isAbsolute ? "absolute" : "ratio",
          application_method: isStock
            ? "sales_capacity_cap"
            : isAbsolute
              ? "additive"
              : "multiplicative",
          source_type: isContext ? "historical_evidence" : "user_hypothesis",
          context_signal_id: item.context_signal_id ?? null,
          context_impact_estimate_id: item.context_impact_estimate_id ?? null,
          source_note: isContext
            ? "Asociación histórica descriptiva seleccionada por el usuario."
            : "Hipótesis declarada manualmente por el usuario.",
        };
      }),
    }),
  });
}

export function executeScenario(scenarioId: string): Promise<ScenarioRun> {
  return apiRequest(`/api/v1/scenarios/${scenarioId}/execute`, { method: "POST" });
}
