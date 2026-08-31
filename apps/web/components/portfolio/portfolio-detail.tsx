import { Database, ShieldAlert } from "lucide-react";

import type { PortfolioItem, PortfolioRun } from "@/lib/portfolio-types";
import { translateFrequency, ui } from "@/lib/i18n";

function number(value: number | null, digits = 2) {
  return value == null ? "—" : new Intl.NumberFormat("es-PE", { maximumFractionDigits: digits }).format(value);
}

export function PortfolioDetail({ item, run }: { item: PortfolioItem | null; run: PortfolioRun }) {
  const copy = ui.portfolio;
  if (!item) return <section className="pf-panel pf-empty-detail">{copy.detail.select}</section>;
  const coverageFormula = item.inventory_coverage == null
    ? copy.detail.coverageUnavailable
    : `${number(item.current_inventory)} / ${number(item.forecast_average)} = ${number(item.inventory_coverage)} ${copy.periods[item.forecast_frequency as keyof typeof copy.periods] ?? copy.periods.default}`;
  return (
    <section className="pf-detail-grid">
      <article className="pf-panel">
        <div className="pf-heading"><div><span>{copy.detail.index}</span><h2>{item.product ?? copy.allProducts} · {item.location ?? copy.allLocations}</h2></div><span className={`pf-risk pf-risk--${item.risk_level}`}>{copy.risks[item.risk_level]}</span></div>
        <div className="pf-metric-grid"><div><span>{copy.detail.total}</span><strong>{number(item.forecast_total)}</strong></div><div><span>{copy.detail.average}</span><strong>{number(item.forecast_average)}</strong></div><div><span>{copy.detail.peak}</span><strong>{number(item.forecast_peak)}</strong></div><div><span>{copy.detail.minimum}</span><strong>{number(item.forecast_minimum)}</strong></div><div><span>{copy.detail.variability}</span><strong>{item.forecast_variability == null ? "—" : `${number(item.forecast_variability * 100, 1)}%`}</strong></div><div><span>{copy.detail.coverage}</span><strong>{item.inventory_coverage == null ? copy.notCalculable : number(item.inventory_coverage)}</strong></div></div>
        <div className="pf-formula"><span>{copy.detail.formula}</span><code>{coverageFormula}</code></div>
        <div className="pf-inputs"><h3>{copy.detail.inputs}</h3>{Object.entries(item.operational_inputs).map(([key, value]) => <div key={key}><span>{copy.inputLabels[key as keyof typeof copy.inputLabels] ?? key}</span><strong className={`pf-input-status pf-input-status--${value.status}`}>{value.status === "available" ? number(value.value) : copy.inputStatuses[value.status]}</strong></div>)}</div>
      </article>
      <article className="pf-panel pf-explanation">
        <div className="pf-heading"><div><span>{copy.explanation.index}</span><h2>{copy.explanation.title}</h2></div><ShieldAlert size={18} /></div>
        <div><span>{copy.explanation.detected}</span><p>{copy.reasons[item.priority_reasons[0] as keyof typeof copy.reasons] ?? copy.reasons.operational_data_incomplete}</p></div>
        <div><span>{copy.explanation.why}</span><p>{copy.explanation.whyText}</p></div>
        <div><span>{copy.explanation.used}</span><p>{copy.explanation.usedText.replace("{champion}", item.champion).replace("{frequency}", translateFrequency(item.forecast_frequency))}</p></div>
        <div><span>{copy.explanation.missing}</span><p>{item.missing_inputs.length ? item.missing_inputs.map((key) => copy.inputLabels[key as keyof typeof copy.inputLabels] ?? key).join(" · ") : copy.explanation.noneMissing}</p></div>
        <div><span>{copy.explanation.priority}</span><p>{copy.explanation.priorityText.replace("{score}", number(item.priority_score)).replace("{status}", item.score_status === "partial" ? copy.partialScore : copy.completeScore)}</p></div>
        <div><span>{copy.explanation.boundary}</span><p>{copy.explanation.boundaryText}</p></div>
      </article>
      <article className="pf-panel pf-audit">
        <div className="pf-heading"><div><span>{copy.audit.index}</span><h2>{copy.audit.title}</h2></div><Database size={18} /></div>
        <dl><div><dt>Portfolio Run ID</dt><dd>{run.id}</dd></div><div><dt>Forecast Run ID</dt><dd>{item.forecast_run_id ?? copy.demo.noForecastRun}</dd></div><div><dt>{copy.audit.version}</dt><dd>{run.calculation_version}</dd></div><div><dt>Cutoff</dt><dd>{new Date(run.cutoff).toLocaleString("es-PE")}</dd></div><div><dt>{copy.audit.created}</dt><dd>{new Date(run.created_at).toLocaleString("es-PE")}</dd></div><div><dt>{copy.audit.source}</dt><dd>{run.source_mode === "demo" ? copy.demo.badge : copy.audit.official}</dd></div></dl>
      </article>
    </section>
  );
}
