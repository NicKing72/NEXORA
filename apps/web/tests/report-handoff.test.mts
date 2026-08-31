import assert from "node:assert/strict";
import test from "node:test";

import { buildReportsHref, readReportHandoff } from "../lib/report-handoff.ts";

const ids = {
  forecast_run_id: "11111111-1111-4111-8111-111111111111",
  scenario_run_id: "22222222-2222-4222-8222-222222222222",
  scor_assessment_id: "33333333-3333-4333-8333-333333333333",
  portfolio_run_id: "44444444-4444-4444-8444-444444444444",
  decision_run_id: "55555555-5555-4555-8555-555555555555",
  explanation_run_id: "66666666-6666-4666-8666-666666666666",
};

test("handoff de reporte preserva solo UUID explícitos y su orden estable", () => {
  assert.equal(
    buildReportsHref(ids),
    `/reports?forecast_run_id=${ids.forecast_run_id}&scenario_run_id=${ids.scenario_run_id}&scor_assessment_id=${ids.scor_assessment_id}&portfolio_run_id=${ids.portfolio_run_id}&decision_run_id=${ids.decision_run_id}&explanation_run_id=${ids.explanation_run_id}`,
  );
});

test("handoff de Forecast no infiere capas posteriores", () => {
  assert.equal(buildReportsHref({ forecast_run_id: ids.forecast_run_id }), `/reports?forecast_run_id=${ids.forecast_run_id}`);
});

test("valores ausentes no se convierten en parámetros ni sustitutos", () => {
  assert.equal(buildReportsHref({ forecast_run_id: null, decision_run_id: "" }), "/reports");
});

test("lectura conserva UUID solicitado sin resolver por posición", () => {
  const requested = readReportHandoff(`?portfolio_run_id=${ids.portfolio_run_id}&forecast_run_id=${ids.forecast_run_id}`);
  assert.equal(requested.forecast_run_id, ids.forecast_run_id);
  assert.equal(requested.portfolio_run_id, ids.portfolio_run_id);
  assert.equal(requested.scenario_run_id, null);
});

test("una pestaña nueva de Reportes permanece limpia", () => {
  assert.deepEqual(readReportHandoff(""), {
    forecast_run_id: null,
    scenario_run_id: null,
    scor_assessment_id: null,
    portfolio_run_id: null,
    decision_run_id: null,
    explanation_run_id: null,
  });
});
