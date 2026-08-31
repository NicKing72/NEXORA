import { apiRequest } from "@/lib/api-client";
import { ui } from "@/lib/i18n";
import type {
  ForecastRunSummary,
  OperationalDraft,
  PortfolioPreflight,
  PortfolioRun,
  PortfolioRunSummary,
} from "@/lib/portfolio-types";

type PortfolioPayload = {
  forecastRunIds: string[];
  datasetId: string | null;
  cutoff: string;
  operationalDrafts?: Record<string, OperationalDraft>;
};

function payload(input: PortfolioPayload) {
  const operational_inputs: Record<string, Record<string, object>> = {};
  Object.entries(input.operationalDrafts ?? {}).forEach(([runId, draft]) => {
    const values = Object.entries(draft).filter(([, value]) => value.trim() !== "");
    if (!values.length) return;
    operational_inputs[runId] = Object.fromEntries(values.map(([field, value]) => [
      field,
      {
        value: Number(value),
        status: "available",
        available_at: input.cutoff,
        source_type: "manual",
        source_reference: "portfolio_ui",
      },
    ]));
  });
  return {
    dataset_id: input.datasetId,
    forecast_run_ids: input.forecastRunIds,
    cutoff: input.cutoff,
    filters: {},
    operational_inputs,
  };
}

export function listPortfolioForecasts(): Promise<ForecastRunSummary[]> {
  return apiRequest(
    "/api/v1/forecast-runs",
    undefined,
    { fallbackMessage: ui.portfolio.errors.forecastLoad },
  );
}

export function preflightPortfolio(input: PortfolioPayload): Promise<PortfolioPreflight> {
  return apiRequest(
    "/api/v1/portfolio/preflight",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload(input)),
    },
    { fallbackMessage: ui.portfolio.errors.preflight },
  );
}

export function createPortfolio(input: PortfolioPayload): Promise<PortfolioRun> {
  return apiRequest(
    "/api/v1/portfolio",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload(input)),
    },
    { fallbackMessage: ui.portfolio.errors.create },
  );
}

export function regeneratePortfolioDemo(): Promise<PortfolioRun> {
  return apiRequest(
    "/api/v1/portfolio/demo/regenerate",
    { method: "POST" },
    { fallbackMessage: ui.portfolio.errors.demoUnavailable },
  );
}

export function listPortfolioRuns(): Promise<PortfolioRunSummary[]> {
  return apiRequest(
    "/api/v1/portfolio",
    undefined,
    { fallbackMessage: ui.portfolio.errors.historyLoad },
  );
}

export function getPortfolioRun(runId: string): Promise<PortfolioRun> {
  return apiRequest(
    `/api/v1/portfolio/${runId}`,
    undefined,
    { fallbackMessage: ui.portfolio.errors.recovery },
  );
}
