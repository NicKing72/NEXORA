import assert from "node:assert/strict";
import test from "node:test";

import {
  buildDecisionCenterHref,
  parseDecisionHandoff,
  resolveDecisionRunHandoff,
  resolveExactSelection,
} from "../lib/decision-handoff.ts";

const fullRun = {
  id: "decision-1",
  forecast_run_id: "forecast-1",
  scenario_run_id: "scenario-1",
  scor_assessment_id: "scor-1",
  portfolio_run_id: "portfolio-1",
};

test("roundtrip preserves Scenario, SCOR, Portfolio and Decision by UUID", () => {
  const href = buildDecisionCenterHref({
    forecastRunId: fullRun.forecast_run_id,
    layers: {
      scenario: { id: fullRun.scenario_run_id },
      scor: { id: fullRun.scor_assessment_id },
      portfolio: { id: fullRun.portfolio_run_id },
      decision: { id: fullRun.id },
    },
  });
  const requested = parseDecisionHandoff(href.split("?")[1]);
  assert.deepEqual(resolveDecisionRunHandoff(requested, fullRun), { ok: true, context: fullRun });
});

test("forecast-only handoff keeps every downstream layer absent", () => {
  const requested = parseDecisionHandoff("?forecast_run_id=forecast-1");
  assert.equal(requested.forecastRunId, "forecast-1");
  assert.equal(requested.scenarioRunId, null);
  assert.equal(requested.scorAssessmentId, null);
  assert.equal(requested.portfolioRunId, null);
  assert.equal(requested.decisionRunId, null);
});

test("a deliberately absent portfolio is not inferred", () => {
  const run = { ...fullRun, portfolio_run_id: null };
  const requested = parseDecisionHandoff(
    buildDecisionCenterHref({
      forecastRunId: run.forecast_run_id,
      layers: {
        scenario: { id: run.scenario_run_id },
        scor: { id: run.scor_assessment_id },
        portfolio: null,
        decision: { id: run.id },
      },
    }).split("?")[1],
  );
  assert.equal(requested.portfolioRunId, null);
  assert.deepEqual(resolveDecisionRunHandoff(requested, run), { ok: true, context: run });
});

test("an incompatible UUID rejects the Decision Run without fallback", () => {
  const requested = parseDecisionHandoff(
    "?forecast_run_id=forecast-1&portfolio_run_id=portfolio-other&decision_run_id=decision-1",
  );
  assert.deepEqual(resolveDecisionRunHandoff(requested, fullRun), {
    ok: false,
    field: "portfolioRunId",
  });
});

test("a nonexistent UUID remains unselected", () => {
  assert.deepEqual(resolveExactSelection("missing", ["available-1", "available-2"]), {
    value: "",
    unavailable: true,
  });
});

test("two compatible resources are resolved by UUID rather than position", () => {
  assert.deepEqual(resolveExactSelection("available-2", ["available-1", "available-2"]), {
    value: "available-2",
    unavailable: false,
  });
});

test("F5 parsing is deterministic and idempotent", () => {
  const href = buildDecisionCenterHref({
    forecastRunId: fullRun.forecast_run_id,
    layers: {
      scenario: { id: fullRun.scenario_run_id },
      scor: { id: fullRun.scor_assessment_id },
      portfolio: { id: fullRun.portfolio_run_id },
      decision: { id: fullRun.id },
    },
  });
  const search = href.slice(href.indexOf("?"));
  assert.deepEqual(parseDecisionHandoff(search), parseDecisionHandoff(search));
});

test("resolving historical context does not mutate the frozen run", () => {
  const before = structuredClone(fullRun);
  const requested = parseDecisionHandoff(
    "?forecast_run_id=forecast-1&scenario_run_id=scenario-1&scor_assessment_id=scor-1&portfolio_run_id=portfolio-1&decision_run_id=decision-1",
  );
  resolveDecisionRunHandoff(requested, fullRun);
  assert.deepEqual(fullRun, before);
});
