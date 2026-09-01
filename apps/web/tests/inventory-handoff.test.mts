import assert from "node:assert/strict";
import test from "node:test";

import { inventoryDemoDraft, inventoryDemoPortfolio, inventoryDemoSources, inventoryRunFromSearch, inventoryRunUrl, inventoryWorkspaceFromRun } from "../lib/inventory-handoff.ts";

const id = "123e4567-e89b-12d3-a456-426614174000";

test("Inventory Run survives an exact F5 URL roundtrip", () => {
  const url = inventoryRunUrl(id);
  assert.equal(url, `/inventory?inventory_run_id=${id}`);
  assert.equal(inventoryRunFromSearch(url.split("?")[1] ?? ""), id);
});

test("a clean Inventory tab does not inherit historical selection", () => {
  assert.equal(inventoryRunFromSearch(""), null);
});

test("an invalid Inventory UUID is never replaced by another run", () => {
  assert.equal(inventoryRunFromSearch("inventory_run_id=first-compatible"), null);
});

test("a persisted Inventory Run restores its exact sources and declared inputs", () => {
  const restored = inventoryWorkspaceFromRun({
    forecast_run_id: "forecast-exact",
    scenario_run_id: "scenario-exact",
    portfolio_run_id: "portfolio-exact",
    cutoff: "2026-08-31T23:32:00-05:00",
    assumptions: { include_in_transit: true },
    items: [{ inputs: {
      inventory_on_hand: { status: "available", value: 500 },
      holding_rate: { status: "missing", value: null },
    } }],
  }, ["inventory_on_hand", "holding_rate"]);

  assert.deepEqual(restored, {
    forecastId: "forecast-exact",
    scenarioId: "scenario-exact",
    portfolioId: "portfolio-exact",
    cutoff: "2026-08-31T23:32:00-05:00",
    includeTransit: true,
    draft: { inventory_on_hand: "500", holding_rate: "" },
  });
});

test("the approved Inventory demo resolves exact compatible sources deterministically", () => {
  const sources = inventoryDemoSources([
    { id: "daily-newer", status: "completed", frequency: "daily", requested_horizon: 30, champion_model: "holt_winters_additive", created_at: "2026-09-01T11:00:00Z" },
    { id: "weekly-older", status: "completed", frequency: "weekly", requested_horizon: 12, champion_model: "moving_average", created_at: "2026-08-30T10:00:00Z" },
    { id: "weekly-approved", status: "completed", frequency: "weekly", requested_horizon: 12, champion_model: "moving_average", created_at: "2026-08-31T10:00:00Z" },
  ], [
    { id: "scenario-older", forecast_run_id: "weekly-approved", status: "completed", created_at: "2026-08-31T10:30:00Z" },
    { id: "scenario-approved", forecast_run_id: "weekly-approved", status: "completed", created_at: "2026-08-31T11:00:00Z" },
    { id: "scenario-wrong", forecast_run_id: "weekly-older", status: "completed", created_at: "2026-09-01T12:00:00Z" },
  ]);

  assert.deepEqual(sources, { forecastId: "weekly-approved", scenarioId: "scenario-approved" });
  assert.equal(inventoryDemoPortfolio([
    { id: "portfolio-wrong", created_at: "2026-09-01T12:00:00Z", forecast_run_ids: ["daily-newer"] },
    { id: "portfolio-approved", created_at: "2026-08-31T12:00:00Z", forecast_run_ids: ["weekly-approved"] },
  ], sources?.forecastId ?? ""), "portfolio-approved");
  assert.equal(inventoryDemoDraft().holding_rate, "");
  assert.equal(inventoryDemoDraft().inventory_on_hand, "500");
});
