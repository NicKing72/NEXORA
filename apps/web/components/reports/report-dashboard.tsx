import { Download, ExternalLink, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { ReportSectionView } from "@/components/reports/report-section-view";
import { ui } from "@/lib/i18n";
import { reportExportUrl } from "@/lib/report-api";
import type { ReportRun } from "@/lib/report-types";

export function ReportDashboard({ run }: Readonly<{ run: ReportRun }>) {
  const copy = ui.reports.dashboard;
  const scope = run.scope;
  const decisionParameters = new URLSearchParams();
  if (run.forecast_run_id) decisionParameters.set("forecast_run_id", run.forecast_run_id);
  if (run.scenario_run_id) decisionParameters.set("scenario_run_id", run.scenario_run_id);
  if (run.scor_assessment_id) decisionParameters.set("scor_assessment_id", run.scor_assessment_id);
  if (run.portfolio_run_id) decisionParameters.set("portfolio_run_id", run.portfolio_run_id);
  if (run.decision_run_id) decisionParameters.set("decision_run_id", run.decision_run_id);
  return <>
    <section className="rp-panel rp-dashboard">
      <div className="rp-section-heading"><div><span>{copy.index}</span><h2>{copy.title}</h2></div>{run.is_demo && <strong className="rp-demo-badge">{copy.demo}</strong>}</div>
      <div className="rp-dashboard-grid">
        <div><small>{copy.id}</small><strong title={run.id}>{run.id.slice(0, 8)}</strong></div><div><small>{copy.type}</small><strong>{ui.reports.types[run.report_type]}</strong></div><div><small>{copy.status}</small><strong>{run.status}</strong></div><div><small>{copy.cutoff}</small><strong>{new Date(run.report_cutoff).toLocaleString("es-PE")}</strong></div><div><small>{copy.dataset}</small><strong>{run.dataset_id ?? (run.is_demo ? "DEMO" : "—")}</strong></div><div><small>{copy.scope}</small><strong>{String(scope.product ?? "Serie agregada")} · {String(scope.location ?? "Todas")}</strong></div><div><small>{copy.layers}</small><strong>{run.coverage.included_layers.join(" · ") || "—"}</strong></div><div><small>{copy.coverage}</small><strong>{Math.round(run.coverage.ratio * 100)}% · {ui.reports.coverage[run.coverage.status]}</strong></div><div><small>{copy.warnings}</small><strong>{run.warning_count}</strong></div>
      </div>
      <div className="rp-export-actions"><a href={reportExportUrl(run.id, "html")} target="_blank" rel="noreferrer"><ExternalLink size={15} />{copy.print}</a><a href={reportExportUrl(run.id, "json")} target="_blank" rel="noreferrer"><Download size={15} />{copy.json}</a><a href={reportExportUrl(run.id, "csv")} target="_blank" rel="noreferrer"><Download size={15} />{copy.csv}</a></div>
      <div className="rp-source-links" aria-label={copy.sourceLinks}>
        <small>{copy.sourceLinks}</small>
        <div>
          {run.forecast_run_id && <Link href={`/forecast-lab?forecast_run_id=${run.forecast_run_id}`}>{copy.viewForecast}</Link>}
          {run.scor_assessment_id && <Link href={`/scor-diagnostic?assessment_id=${run.scor_assessment_id}`}>{copy.viewScor}</Link>}
          {run.portfolio_run_id && <Link href={`/portfolio?portfolio_run_id=${run.portfolio_run_id}`}>{copy.viewPortfolio}</Link>}
          {run.decision_run_id && <Link href={`/decision-center?${decisionParameters.toString()}`}>{copy.viewDecision}</Link>}
          {run.explanation_run_id && <Link href={`/model-explain?forecast_run_id=${run.forecast_run_id ?? ""}&explanation_id=${run.explanation_run_id}`}>{copy.viewExplanation}</Link>}
        </div>
      </div>
      <p className="rp-boundary"><ShieldCheck size={16} />{copy.boundary}</p>
    </section>
    {run.sections.map((section) => <ReportSectionView key={section.id} section={section} />)}
  </>;
}
