import { Ban, CheckCircle2, Link2, ShieldAlert } from "lucide-react";

import type { ContextSignal, KnowledgeType, ScopeType, SignalFamily, SignalStatus, SourceType } from "@/lib/context-types";
import { ui } from "@/lib/i18n";

function formatInstant(value: string | null): string {
  if (!value) return ui.contextRadar.detail.notProvided;
  return new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

type Props = { signal: ContextSignal | null; onStatus: (status: "dismissed" | "reviewed") => void };

export function SignalDetail({ signal, onStatus }: Readonly<Props>) {
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
      <div className="cx-impact"><ShieldAlert size={17} /><span><small>{copy.impact}</small><strong>{copy.notEstimated}</strong><p>{copy.boundary}</p></span></div>
      <div className="cx-audit-stamps"><span>{copy.created}: {formatInstant(signal.created_at)}</span><span>{copy.updated}: {formatInstant(signal.updated_at)}</span></div>
      {!(["dismissed", "expired"] as SignalStatus[]).includes(signal.status) && <div className="cx-detail-actions"><button type="button" onClick={() => onStatus("reviewed")}><CheckCircle2 size={14} />{ui.contextRadar.actions.review}</button><button type="button" className="cx-danger-action" onClick={() => onStatus("dismissed")}><Ban size={14} />{ui.contextRadar.actions.dismiss}</button></div>}
    </section>
  );
}
