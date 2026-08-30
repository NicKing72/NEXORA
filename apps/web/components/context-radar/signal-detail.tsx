import { Ban, CheckCircle2, Link2, RefreshCw, ShieldAlert } from "lucide-react";

import type { ContextAnalogy, ContextImpactEstimate, ContextSignal, KnowledgeType, ScopeType, SignalFamily, SignalStatus, SourceType } from "@/lib/context-types";
import { ui } from "@/lib/i18n";

function formatInstant(value: string | null): string {
  if (!value) return ui.contextRadar.detail.notProvided;
  return new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function formatNumber(value: number | null): string {
  return value === null ? "—" : new Intl.NumberFormat("es-PE", { maximumFractionDigits: 2 }).format(value);
}

function formatPercent(value: number | null): string {
  if (value === null) return "—";
  return new Intl.NumberFormat("es-PE", { style: "percent", maximumFractionDigits: 1, signDisplay: "always" }).format(value);
}

type Props = {
  signal: ContextSignal | null;
  impact: ContextImpactEstimate | null;
  analogy: ContextAnalogy | null;
  estimating: boolean;
  onEstimate: () => void;
  onStatus: (status: "dismissed" | "reviewed") => void;
};

type ImpactEvidenceProps = Omit<Props, "signal" | "onStatus"> & { signal: ContextSignal };

function ImpactEvidence({ impact, analogy, signal, estimating, onEstimate }: Readonly<ImpactEvidenceProps>) {
  const copy = ui.contextRadar.detail;
  const reasons = ui.contextRadar.impact.reasons;
  const methods = ui.contextRadar.impact.methods;
  if (impact?.reason_code === "demand_censored_by_stockout" || signal.signal_type === "stockout" && impact) {
    return <div className="cx-impact cx-impact--censored"><ShieldAlert size={17} /><span><small>{copy.censored}</small><strong>{copy.censored}</strong><p>{copy.censoredExplanation}</p><p>{copy.noForecastApplication}</p></span></div>;
  }
  if (analogy?.status === "available") {
    return <div className="cx-impact cx-impact--analogy"><ShieldAlert size={17} /><span><small>{copy.historicalEffect}</small><strong>{copy.median}: {formatPercent(analogy.median_relative_delta)}</strong><p>{copy.observedRange}: {formatPercent(analogy.minimum_relative_delta)} a {formatPercent(analogy.maximum_relative_delta)} · {copy.comparableEvents.replace("{count}", String(analogy.comparable_events))}</p><p>{copy.noForecastApplication}</p></span></div>;
  }
  if (impact?.status === "estimated") {
    const evidence = ui.contextRadar.impact.evidenceLevels[impact.evidence_level];
    const method = methods[impact.method as keyof typeof methods] ?? impact.method;
    return <div className="cx-impact cx-impact--estimated"><ShieldAlert size={17} /><span><small>{copy.observedImpact}</small><strong>{formatPercent(impact.relative_delta)} <em>{copy.comparableBaseline}</em></strong><div className="cx-impact-metrics"><span><small>{copy.evidence}</small><b>{evidence} · {impact.evidence_score}/100</b></span><span><small>{copy.baseline}</small><b>{formatNumber(impact.baseline_value)}</b></span><span><small>{copy.observedDemand}</small><b>{formatNumber(impact.observed_value)}</b></span><span><small>{copy.eventPeriods}</small><b>{impact.event_periods}</b></span></div><details><summary>{copy.evidenceDetail}</summary><p>{copy.method}: {method}</p><p>{copy.referencePeriods}: {impact.reference_periods} · {copy.evidenceScore}: {impact.evidence_score}/100</p><p>{impact.notes} {copy.noCausality}</p></details><p>{copy.boundary}</p></span></div>;
  }
  if (impact) {
    const reason = impact.reason_code ? reasons[impact.reason_code as keyof typeof reasons] : impact.notes;
    return <div className="cx-impact"><ShieldAlert size={17} /><span><small>{copy.impact}</small><strong>{copy.insufficient}</strong><p>{reason}</p><p>{copy.referencePeriods}: {impact.reference_periods} · {copy.eventPeriods}: {impact.event_periods}</p><p>{copy.boundary}</p></span></div>;
  }
  return <div className="cx-impact"><ShieldAlert size={17} /><span><small>{copy.impact}</small><strong>{copy.notEstimated}</strong><p>{copy.boundary}</p><button type="button" className="cx-impact-action" disabled={estimating} onClick={onEstimate}>{estimating && <RefreshCw size={13} />}{estimating ? copy.estimating : copy.estimate}</button></span></div>;
}

export function SignalDetail({ signal, impact, analogy, estimating, onEstimate, onStatus }: Readonly<Props>) {
  const copy = ui.contextRadar.detail;
  if (!signal) return <section className="cx-panel cx-detail cx-detail--empty"><div className="cx-heading"><div><span className="section-index">{copy.index}</span><h2>{copy.title}</h2></div></div><p>{copy.select}</p></section>;
  const values = [
    [copy.family, ui.contextRadar.families[signal.signal_family as SignalFamily]],
    [copy.type, signal.signal_type],
    [copy.start, formatInstant(signal.event_start)],
    [copy.end, signal.event_end ? formatInstant(signal.event_end) : copy.noEnd],
    [copy.observed, formatInstant(signal.observed_at)],
    [copy.available, formatInstant(signal.available_at)],
    [copy.source, `${ui.contextRadar.sources[signal.source_type as SourceType]} · ${signal.source_name}`],
    [copy.confidence, signal.confidence === null ? copy.notProvided : `${Math.round(signal.confidence * 100)}%`],
    [copy.knowledge, ui.contextRadar.knowledgeTypes[signal.knowledge_type as KnowledgeType]],
    [copy.scope, ui.contextRadar.scopes[signal.scope_type as ScopeType]],
    [copy.status, ui.contextRadar.statuses[signal.status as SignalStatus]],
  ];
  return (
    <section className="cx-panel cx-detail" aria-labelledby="cx-detail-title">
      <div className="cx-heading"><div><span className="section-index">{copy.index}</span><h2 id="cx-detail-title">{signal.title}</h2></div><span className={`cx-status cx-status--${signal.status}`}>{ui.contextRadar.statuses[signal.status as SignalStatus]}</span></div>
      <p className="cx-description">{signal.description}</p>
      <dl>{values.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
      {signal.source_reference && <p className="cx-source-reference"><Link2 size={13} />{signal.source_reference}</p>}
      <ImpactEvidence signal={signal} impact={impact} analogy={analogy} estimating={estimating} onEstimate={onEstimate} />
      <div className="cx-audit-stamps"><span>{copy.created}: {formatInstant(signal.created_at)}</span><span>{copy.updated}: {formatInstant(signal.updated_at)}</span></div>
      {!("dismissed expired".split(" ") as SignalStatus[]).includes(signal.status) && <div className="cx-detail-actions"><button type="button" onClick={() => onStatus("reviewed")}><CheckCircle2 size={14} />{ui.contextRadar.actions.review}</button><button type="button" className="cx-danger-action" onClick={() => onStatus("dismissed")}><Ban size={14} />{ui.contextRadar.actions.dismiss}</button></div>}
    </section>
  );
}
