export type DecisionHandoff = {
  forecastRunId: string | null;
  scenarioRunId: string | null;
  scorAssessmentId: string | null;
  portfolioRunId: string | null;
  decisionRunId: string | null;
};

export type DecisionRunContext = {
  id: string;
  forecast_run_id: string;
  scenario_run_id: string | null;
  scor_assessment_id: string | null;
  portfolio_run_id: string | null;
};

type ExplanationLayer = Record<string, unknown> | null;

const PARAMS = {
  forecastRunId: "forecast_run_id",
  scenarioRunId: "scenario_run_id",
  scorAssessmentId: "scor_assessment_id",
  portfolioRunId: "portfolio_run_id",
  decisionRunId: "decision_run_id",
} as const;

function layerId(layer: ExplanationLayer) {
  return typeof layer?.id === "string" ? layer.id : null;
}

export function buildDecisionCenterHref(input: {
  forecastRunId: string;
  layers: Record<string, ExplanationLayer>;
}) {
  const parameters = new URLSearchParams();
  parameters.set(PARAMS.forecastRunId, input.forecastRunId);
  const values: Array<[string, string | null]> = [
    [PARAMS.scenarioRunId, layerId(input.layers.scenario)],
    [PARAMS.scorAssessmentId, layerId(input.layers.scor)],
    [PARAMS.portfolioRunId, layerId(input.layers.portfolio)],
    [PARAMS.decisionRunId, layerId(input.layers.decision)],
  ];
  values.forEach(([key, value]) => { if (value) parameters.set(key, value); });
  return `/decision-center?${parameters.toString()}`;
}

export function buildDecisionCenterHrefFromRun(run: DecisionRunContext) {
  return buildDecisionCenterHref({
    forecastRunId: run.forecast_run_id,
    layers: {
      scenario: run.scenario_run_id ? { id: run.scenario_run_id } : null,
      scor: run.scor_assessment_id ? { id: run.scor_assessment_id } : null,
      portfolio: run.portfolio_run_id ? { id: run.portfolio_run_id } : null,
      decision: { id: run.id },
    },
  });
}

export function parseDecisionHandoff(search: string): DecisionHandoff {
  const parameters = new URLSearchParams(search);
  return {
    forecastRunId: parameters.get(PARAMS.forecastRunId),
    scenarioRunId: parameters.get(PARAMS.scenarioRunId),
    scorAssessmentId: parameters.get(PARAMS.scorAssessmentId),
    portfolioRunId: parameters.get(PARAMS.portfolioRunId),
    decisionRunId: parameters.get(PARAMS.decisionRunId),
  };
}

export function resolveDecisionRunHandoff(
  requested: DecisionHandoff,
  stored: DecisionRunContext,
): { ok: true; context: DecisionRunContext } | { ok: false; field: keyof DecisionHandoff } {
  const comparisons: Array<[keyof DecisionHandoff, string | null, string | null]> = [
    ["decisionRunId", requested.decisionRunId, stored.id],
    ["forecastRunId", requested.forecastRunId, stored.forecast_run_id],
    ["scenarioRunId", requested.scenarioRunId, stored.scenario_run_id],
    ["scorAssessmentId", requested.scorAssessmentId, stored.scor_assessment_id],
    ["portfolioRunId", requested.portfolioRunId, stored.portfolio_run_id],
  ];
  const mismatch = comparisons.find(([, expected, actual]) => expected !== null && expected !== actual);
  return mismatch ? { ok: false, field: mismatch[0] } : { ok: true, context: stored };
}

export function resolveExactSelection(requestedId: string | null, availableIds: readonly string[]) {
  if (!requestedId) return { value: "", unavailable: false };
  return availableIds.includes(requestedId)
    ? { value: requestedId, unavailable: false }
    : { value: "", unavailable: true };
}
