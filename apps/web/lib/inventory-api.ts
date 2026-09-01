import { apiRequest } from "@/lib/api-client";
import type {
  ForecastRunSummary, InventoryDraft, InventoryPreflight, InventoryRun,
  InventoryRunSummary, PortfolioRun, PortfolioRunSummary, ScenarioRunSummary,
} from "@/lib/inventory-types";

export type InventoryPayload = {
  forecastRunId: string; scenarioRunId: string | null; portfolioRunId: string | null;
  cutoff: string; draft: InventoryDraft; includeInTransit: boolean; frequency?: string;
};

const inputUnits: Record<keyof InventoryDraft, string> = {
  inventory_on_hand: "units", inventory_in_transit: "units", safety_stock: "units",
  lead_time: "days", service_level: "ratio", unit_cost: "currency/unit",
  order_cost: "currency/order", holding_cost: "currency/unit/year", holding_rate: "ratio/year",
  moq: "units", lot_multiple: "units", capacity: "units", committed_inventory: "units",
  backorders: "units",
};

function body(input: InventoryPayload) {
  const units = { ...inputUnits, lead_time: input.frequency === "weekly" ? "weeks" : input.frequency === "monthly" ? "months" : "days" };
  const operational_inputs = Object.fromEntries(Object.entries(input.draft).filter(([, value]) => value !== "").map(([name, value]) => [name, {
    value: Number(value), status: "available", unit: units[name as keyof InventoryDraft],
    available_at: input.cutoff, source_type: "manual", source_reference: "inventory_ui",
  }]));
  return { forecast_run_id: input.forecastRunId, scenario_run_id: input.scenarioRunId,
    portfolio_run_id: input.portfolioRunId, cutoff: input.cutoff,
    include_in_transit: input.includeInTransit, operational_inputs };
}

export const listInventoryForecasts = () => apiRequest<ForecastRunSummary[]>("/api/v1/forecast-runs");
export const listInventoryScenarios = () => apiRequest<ScenarioRunSummary[]>("/api/v1/scenarios");
export const listInventoryPortfolios = () => apiRequest<PortfolioRunSummary[]>("/api/v1/portfolio");
export const getInventoryPortfolio = (id: string) => apiRequest<PortfolioRun>(`/api/v1/portfolio/${id}`);
export const listInventoryRuns = () => apiRequest<InventoryRunSummary[]>("/api/v1/inventory");
export const getInventoryRun = (id: string) => apiRequest<InventoryRun>(`/api/v1/inventory/${id}`);
export const preflightInventory = (input: InventoryPayload) => apiRequest<InventoryPreflight>("/api/v1/inventory/preflight", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body(input)) });
export const createInventory = (input: InventoryPayload) => apiRequest<InventoryRun>("/api/v1/inventory", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body(input)) });
export const regenerateInventoryDemo = () => apiRequest<InventoryRun>("/api/v1/inventory/demo/regenerate", { method: "POST" });
