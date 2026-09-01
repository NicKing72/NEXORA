export function inventoryRunFromSearch(search: string): string | null {
  const value = new URLSearchParams(search).get("inventory_run_id");
  return value && /^[0-9a-f-]{36}$/i.test(value) ? value : null;
}

export function inventoryRunUrl(runId: string): string {
  return `/inventory?inventory_run_id=${encodeURIComponent(runId)}`;
}

type StoredInventoryInput = { status?: unknown; value?: unknown };

type StoredInventoryWorkspace = {
  forecast_run_id: string | null;
  scenario_run_id: string | null;
  portfolio_run_id: string | null;
  cutoff: string;
  assumptions: Record<string, unknown>;
  items: Array<{ inputs: Record<string, StoredInventoryInput> }>;
};

export function inventoryWorkspaceFromRun(
  run: StoredInventoryWorkspace,
  inputNames: readonly string[],
) {
  const inputs = run.items[0]?.inputs ?? {};
  const draft = Object.fromEntries(inputNames.map((name) => {
    const input = inputs[name];
    const value = input?.status === "available" && typeof input.value === "number"
      ? String(input.value)
      : "";
    return [name, value];
  }));

  return {
    forecastId: run.forecast_run_id ?? "",
    scenarioId: run.scenario_run_id ?? "",
    portfolioId: run.portfolio_run_id ?? "",
    cutoff: run.cutoff,
    includeTransit: run.assumptions.include_in_transit === true,
    draft,
  };
}

type DemoForecast = {
  id: string;
  status: string;
  frequency: string;
  requested_horizon: number;
  champion_model: string | null;
  created_at: string;
};

type DemoScenario = {
  id: string;
  forecast_run_id: string;
  status: string;
  created_at: string;
};

type DemoPortfolio = {
  id: string;
  created_at: string;
  forecast_run_ids: string[];
};

const newestFirst = <T extends { id: string; created_at: string }>(left: T, right: T) =>
  right.created_at.localeCompare(left.created_at) || left.id.localeCompare(right.id);

export function inventoryDemoSources(
  forecasts: readonly DemoForecast[],
  scenarios: readonly DemoScenario[],
) {
  const forecast = forecasts
    .filter((item) => item.status === "completed"
      && item.frequency === "weekly"
      && item.requested_horizon === 12
      && item.champion_model === "moving_average"
      && scenarios.some((scenario) => scenario.status === "completed" && scenario.forecast_run_id === item.id))
    .sort(newestFirst)[0];
  if (!forecast) return null;
  const scenario = scenarios
    .filter((item) => item.status === "completed" && item.forecast_run_id === forecast.id)
    .sort(newestFirst)[0];
  return scenario ? { forecastId: forecast.id, scenarioId: scenario.id } : null;
}

export function inventoryDemoPortfolio(
  portfolios: readonly DemoPortfolio[],
  forecastId: string,
): string | null {
  return portfolios
    .filter((item) => item.forecast_run_ids.includes(forecastId))
    .sort(newestFirst)[0]?.id ?? null;
}

export function inventoryDemoDraft() {
  return {
    inventory_on_hand: "500",
    inventory_in_transit: "100",
    safety_stock: "60",
    lead_time: "2",
    service_level: "0.95",
    unit_cost: "20",
    order_cost: "50",
    holding_cost: "4",
    holding_rate: "",
    moq: "100",
    lot_multiple: "25",
    capacity: "800",
    committed_inventory: "30",
    backorders: "20",
  };
}
