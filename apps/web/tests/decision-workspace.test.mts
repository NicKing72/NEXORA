import assert from "node:assert/strict";
import test from "node:test";

import { buildDecisionCenterHrefFromRun } from "../lib/decision-handoff.ts";
import {
  DECISION_WORKSPACE_STORAGE_KEY,
  isRestorableDecisionWorkspace,
  persistDecisionWorkspace,
  readDecisionWorkspace,
} from "../lib/decision-workspace.ts";

class MemoryStorage {
  private values = new Map<string, string>();

  getItem(key: string) {
    return this.values.get(key) ?? null;
  }

  setItem(key: string, value: string) {
    this.values.set(key, value);
  }
}

const firstRun = {
  id: "decision-A",
  forecast_run_id: "forecast-A",
  scenario_run_id: "scenario-A",
  scor_assessment_id: "scor-A",
  portfolio_run_id: "portfolio-A",
};

test("a resolved Decision workspace is restored by the sidebar", () => {
  const storage = new MemoryStorage();
  const href = buildDecisionCenterHrefFromRun(firstRun);
  assert.equal(persistDecisionWorkspace(storage, href), true);
  assert.equal(readDecisionWorkspace(storage), href);
});

test("a new tab without session context keeps the clean Decision Center", () => {
  assert.equal(readDecisionWorkspace(new MemoryStorage()), "/decision-center");
});

test("Decision context is not propagated to unrelated routes", () => {
  assert.equal(isRestorableDecisionWorkspace("/scor-diagnostic?decision_run_id=decision-A"), false);
  assert.equal(isRestorableDecisionWorkspace("/portfolio?forecast_run_id=forecast-A"), false);
});

test("an invalid stored value cannot replace the clean destination", () => {
  const storage = new MemoryStorage();
  storage.setItem(DECISION_WORKSPACE_STORAGE_KEY, "/decision-center?decision_run_id=missing");
  assert.equal(readDecisionWorkspace(storage), "/decision-center");
});

test("a second resolved Decision Run replaces the previous workspace", () => {
  const storage = new MemoryStorage();
  const secondRun = {
    id: "decision-B",
    forecast_run_id: "forecast-B",
    scenario_run_id: null,
    scor_assessment_id: "scor-B",
    portfolio_run_id: null,
  };
  persistDecisionWorkspace(storage, buildDecisionCenterHrefFromRun(firstRun));
  const secondHref = buildDecisionCenterHrefFromRun(secondRun);
  persistDecisionWorkspace(storage, secondHref);
  assert.equal(readDecisionWorkspace(storage), secondHref);
  assert.equal(readDecisionWorkspace(storage).includes("decision-A"), false);
});

test("stored identities remain explicit and ordered deterministically", () => {
  assert.equal(
    buildDecisionCenterHrefFromRun(firstRun),
    "/decision-center?forecast_run_id=forecast-A&scenario_run_id=scenario-A&scor_assessment_id=scor-A&portfolio_run_id=portfolio-A&decision_run_id=decision-A",
  );
});
