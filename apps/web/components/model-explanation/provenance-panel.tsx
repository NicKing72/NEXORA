import { Fingerprint, Layers3 } from "lucide-react";
import Link from "next/link";

import { buildDecisionCenterHref } from "@/lib/decision-handoff";
import type { ExplanationRun } from "@/lib/explanation-types";
import { ui } from "@/lib/i18n";
import { buildReportsHref } from "@/lib/report-handoff";

export function ProvenancePanel({ run }: Readonly<{ run: ExplanationRun }>) {
  const copy = ui.modelExplanation.provenance;
  const snapshot = run.source_snapshot;
  const layerNames = Object.entries(snapshot.layers).filter(([, value]) => value !== null).map(([key]) => key);
  const decision = snapshot.layers.decision;
  const decisionHref = buildDecisionCenterHref({
    forecastRunId: run.forecast_run_id,
    layers: snapshot.layers,
  });
  const reportHref = buildReportsHref({
    forecast_run_id: run.forecast_run_id,
    scenario_run_id: typeof snapshot.layers.scenario?.id === "string" ? snapshot.layers.scenario.id : null,
    scor_assessment_id: typeof snapshot.layers.scor?.id === "string" ? snapshot.layers.scor.id : null,
    portfolio_run_id: typeof snapshot.layers.portfolio?.id === "string" ? snapshot.layers.portfolio.id : null,
    decision_run_id: typeof snapshot.layers.decision?.id === "string" ? snapshot.layers.decision.id : null,
    explanation_run_id: run.id,
  });
  return (
    <section className="mx-panel mx-provenance">
      <div className="mx-section-heading"><div><span>{copy.index}</span><h2>{copy.title}</h2></div><Fingerprint size={18} /></div>
      <dl className="mx-provenance-grid"><div><dt>{copy.forecast}</dt><dd>{run.forecast_run_id}</dd></div><div><dt>{copy.dataset}</dt><dd>{run.dataset_id}</dd></div><div><dt>{copy.dataCutoff}</dt><dd>{snapshot.forecast.data_cutoff}</dd></div><div><dt>{copy.trainingCutoff}</dt><dd>{snapshot.forecast.training_cutoff ?? copy.unavailable}</dd></div><div><dt>{copy.forecastVersion}</dt><dd>{snapshot.forecast.calculation_version ?? copy.unavailable}</dd></div><div><dt>{copy.explanationVersion}</dt><dd>{run.version}</dd></div></dl>
      <div className="mx-layers"><Layers3 size={17} /><span><small>{copy.layers}</small><strong>{layerNames.length ? layerNames.join(" · ") : copy.none}</strong></span></div>
      {decision && typeof decision.id === "string" && <Link className="mx-secondary-action" href={decisionHref}>{copy.backDecision}</Link>}
      <Link className="mx-secondary-action" href={reportHref}>{ui.reports.handoff.create}</Link>
    </section>
  );
}
