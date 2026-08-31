import { Database, Fingerprint, Gauge, Layers3, ShieldAlert } from "lucide-react";

import { ui } from "@/lib/i18n";
import type { ReportSection } from "@/lib/report-types";
import { ReportForecastVisual } from "@/components/reports/report-forecast-visual";

function list(value: unknown) {
  return Array.isArray(value) ? value.map(String) : [];
}

function Executive({ payload }: Readonly<{ payload: Record<string, unknown> }>) {
  const groups = [
    [ui.reports.sections.facts, list(payload.facts)],
    [ui.reports.sections.recommendations, list(payload.recommendations).filter(Boolean)],
    [ui.reports.sections.uncertainty, list(payload.uncertainties)],
    [ui.reports.sections.missing, list(payload.missing_data)],
  ] as const;
  return <div className="rp-executive-grid">{groups.map(([title, items]) => <article key={title}><small>{title}</small>{items.length ? <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p>{ui.reports.sections.noData}</p>}</article>)}</div>;
}

function Forecast({ payload }: Readonly<{ payload: Record<string, unknown> }>) {
  const points = Array.isArray(payload.points) ? payload.points as Array<Record<string, unknown>> : [];
  return <><div className="rp-kpi-row"><div><small>{ui.reports.dashboard.scope}</small><strong>{JSON.stringify(payload.scope)}</strong></div><div><small>Frecuencia</small><strong>{String(payload.frequency ?? "—")}</strong></div><div><small>Horizonte</small><strong>{String(payload.horizon ?? "—")}</strong></div><div><small>Periodos</small><strong>{points.length}</strong></div></div><ReportForecastVisual points={points} /></>;
}

function Validation({ payload }: Readonly<{ payload: Record<string, unknown> }>) {
  const models = Array.isArray(payload.models) ? payload.models as Array<Record<string, unknown>> : [];
  return <div className="rp-table-wrap"><table><thead><tr><th>Ranking</th><th>{ui.reports.sections.model}</th><th>WMAPE</th><th>MAE</th><th>Folds</th></tr></thead><tbody>{models.map((model) => { const metrics = typeof model.metrics === "object" && model.metrics ? model.metrics as Record<string, unknown> : {}; return <tr key={String(model.model_name)}><td>{String(model.rank ?? "—")}</td><td>{String(model.model_name)}</td><td>{metrics.wmape == null ? "—" : `${(Number(metrics.wmape) * 100).toFixed(2)}%`}</td><td>{metrics.mae == null ? "—" : Number(metrics.mae).toFixed(2)}</td><td>{Array.isArray(model.folds) ? model.folds.length : 0}</td></tr>; })}</tbody></table></div>;
}

function record(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function number(value: unknown, digits = 2) {
  return typeof value === "number" ? new Intl.NumberFormat("es-PE", { maximumFractionDigits: digits }).format(value) : "—";
}

function ScenarioEvidence({ payload }: Readonly<{ payload: Record<string, unknown> }>) {
  const scenario = record(payload.scenario);
  const summary = record(scenario.summary);
  return <><div className="rp-kpi-row"><div><small>{ui.reports.sections.baseline}</small><strong>{number(summary.baseline_total)}</strong></div><div><small>{ui.reports.sections.scenario}</small><strong>{number(summary.scenario_total)}</strong></div><div><small>{ui.reports.sections.delta}</small><strong>{typeof summary.relative_delta === "number" ? `${(summary.relative_delta * 100).toFixed(1)}%` : "—"}</strong></div><div><small>Periodos afectados</small><strong>{number(summary.affected_periods, 0)}</strong></div></div><p className="rp-evidence-note">Escenario hipotético; no sustituye ni modifica el pronóstico oficial.</p></>;
}

function ScorEvidence({ payload }: Readonly<{ payload: Record<string, unknown> }>) {
  const assessment = record(payload.assessment);
  const processes = Array.isArray(assessment.processes) ? assessment.processes as Array<Record<string, unknown>> : [];
  return <><div className="rp-kpi-row"><div><small>Periodo</small><strong>{String(assessment.period_start ?? "—").slice(0, 10)} — {String(assessment.period_end ?? "—").slice(0, 10)}</strong></div><div><small>Perfil</small><strong>{String(assessment.benchmark_profile_id ?? "—")}</strong></div><div><small>Versión</small><strong>{String(assessment.algorithm_version ?? "—")}</strong></div><div><small>Estado</small><strong>{String(assessment.status ?? "—")}</strong></div></div>{processes.length > 0 && <div className="rp-table-wrap"><table><thead><tr><th>{ui.reports.sections.process}</th><th>Cobertura</th><th>{ui.reports.sections.gap}</th><th>Ranking</th></tr></thead><tbody>{processes.map((process) => <tr key={String(process.process)}><td>{String(process.process)}</td><td>{typeof process.data_coverage === "number" ? `${(process.data_coverage * 100).toFixed(0)}%` : "—"}</td><td>{number(process.weighted_gap_score)}</td><td>{String(process.rank ?? "—")}</td></tr>)}</tbody></table></div>}</>;
}

function PortfolioEvidence({ payload }: Readonly<{ payload: Record<string, unknown> }>) {
  const portfolio = record(payload.portfolio);
  const items = Array.isArray(portfolio.items) ? portfolio.items as Array<Record<string, unknown>> : [];
  return <><div className="rp-kpi-row"><div><small>Series analizadas</small><strong>{number(portfolio.number_of_series, 0)}</strong></div><div><small>Versión</small><strong>{String(portfolio.calculation_version ?? "—")}</strong></div><div><small>Corte</small><strong>{String(portfolio.cutoff ?? "—").slice(0, 16)}</strong></div><div><small>Fuente</small><strong>{String(portfolio.source_mode ?? "—")}</strong></div></div>{items.length > 0 && <div className="rp-table-wrap"><table><thead><tr><th>Ranking</th><th>Serie</th><th>Priority Score</th><th>Riesgo</th><th>Cobertura</th></tr></thead><tbody>{items.slice(0, 20).map((item) => <tr key={String(item.id ?? item.series_key)}><td>{String(item.rank ?? "—")}</td><td>{String(item.product ?? "Serie agregada")} · {String(item.location ?? "Todas")}</td><td>{number(item.priority_score, 1)}</td><td>{String(item.risk_level ?? "—")}</td><td>{number(item.inventory_coverage)}</td></tr>)}</tbody></table></div>}</>;
}

function DecisionEvidence({ payload }: Readonly<{ payload: Record<string, unknown> }>) {
  const decision = record(payload.decision);
  const recommendations = Array.isArray(decision.recommendations) ? decision.recommendations as Array<Record<string, unknown>> : [];
  return <><div className="rp-kpi-row"><div><small>Recomendaciones</small><strong>{number(decision.recommendation_count, 0)}</strong></div><div><small>Alta / crítica</small><strong>{number(decision.high_priority_count, 0)}</strong></div><div><small>Estado</small><strong>{String(decision.status ?? "—")}</strong></div><div><small>Corte de decisión</small><strong>{String(decision.decision_cutoff ?? "—").slice(0, 16)}</strong></div></div>{recommendations.length > 0 && <div className="rp-table-wrap"><table><thead><tr><th>Ranking</th><th>{ui.reports.sections.priority}</th><th>Recomendación</th><th>Estado</th><th>Soporte</th></tr></thead><tbody>{recommendations.map((item) => <tr key={String(item.id)}><td>{String(item.rank ?? "—")}</td><td>{String(item.priority ?? "—")}</td><td>{String(item.title ?? item.action_type ?? "—")}</td><td>{String(item.status ?? "—")}</td><td>{number(item.support_score, 1)}</td></tr>)}</tbody></table></div>}</>;
}

function ExplanationEvidence({ payload }: Readonly<{ payload: Record<string, unknown> }>) {
  const explanation = record(payload.explanation);
  const snapshot = record(explanation.source_snapshot);
  const layers = record(snapshot.layers);
  return <div className="rp-kpi-row"><div><small>Champion</small><strong>{String(explanation.champion_model ?? "—")}</strong></div><div><small>Frecuencia</small><strong>{String(explanation.frequency ?? "—")}</strong></div><div><small>Versión</small><strong>{String(explanation.version ?? "—")}</strong></div><div><small>Capas posteriores</small><strong>{Object.entries(layers).filter(([, value]) => value !== null).map(([key]) => key).join(" · ") || "Ninguna"}</strong></div></div>;
}

function GenericEvidence({ payload }: Readonly<{ payload: Record<string, unknown> }>) {
  const entries = Object.entries(payload).filter(([key]) => key !== "title");
  return <div className="rp-evidence-grid">{entries.slice(0, 8).map(([key, value]) => <div key={key}><small>{key.replaceAll("_", " ")}</small><strong>{value == null ? ui.reports.sections.noData : typeof value === "object" ? JSON.stringify(value) : String(value)}</strong></div>)}</div>;
}

export function ReportSectionView({ section }: Readonly<{ section: ReportSection }>) {
  const title = String(section.payload.title ?? section.section_type);
  const Icon = section.section_type === "provenance" ? Fingerprint : section.section_type === "risks" ? ShieldAlert : section.section_type === "validation" ? Gauge : section.section_type === "forecast" ? Database : Layers3;
  return (
    <section className={`rp-panel rp-report-section rp-report-section--${section.section_type}`}>
      <div className="rp-section-heading"><div><span>{String(section.position).padStart(2, "0")} /</span><h2>{title}</h2></div><span className="rp-completeness"><Icon size={15} />{section.completeness}</span></div>
      {section.section_type === "executive" ? <Executive payload={section.payload} /> : section.section_type === "forecast" ? <Forecast payload={section.payload} /> : section.section_type === "validation" ? <Validation payload={section.payload} /> : section.section_type === "context_scenario" ? <ScenarioEvidence payload={section.payload} /> : section.section_type === "scor" ? <ScorEvidence payload={section.payload} /> : section.section_type === "portfolio" ? <PortfolioEvidence payload={section.payload} /> : section.section_type === "decisions" ? <DecisionEvidence payload={section.payload} /> : section.section_type === "explanation" ? <ExplanationEvidence payload={section.payload} /> : <GenericEvidence payload={section.payload} />}
      {section.source_references.length > 0 && <div className="rp-source-reference"><Fingerprint size={14} />{section.source_references.map((item) => `${String(item.source_type)} · ${String(item.source_id)}`).join(" · ")}</div>}
    </section>
  );
}
