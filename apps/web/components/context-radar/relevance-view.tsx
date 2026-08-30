import { GitMerge } from "lucide-react";

import type { RelevantSignal } from "@/lib/context-types";
import { interpolate, ui } from "@/lib/i18n";

export function RelevanceView({ matches, seriesLabel }: Readonly<{ matches: RelevantSignal[]; seriesLabel: string }>) {
  const copy = ui.contextRadar.relevance;
  return (
    <section className="cx-panel cx-relevance" aria-labelledby="cx-relevance-title">
      <div className="cx-heading"><div><span className="section-index">{copy.index}</span><h2 id="cx-relevance-title">{interpolate(copy.title, { series: seriesLabel })}</h2><p>{copy.subtitle}</p></div><GitMerge size={19} /></div>
      {matches.length === 0 ? <p className="cx-empty-inline">{copy.none}</p> : <div className="cx-relevance-list">{matches.map(({ signal, match_reasons: reasons }) => <article key={signal.id}><span className="cx-family-mark" data-family={signal.signal_family} /><div><strong>{signal.title}</strong>{reasons.map((reason) => <small key={`${signal.id}-${reason.dimension}`}>{reason.dimension === "scope" ? copy.global : interpolate(copy.reason, { dimension: ui.contextRadar.dimensions[reason.dimension as keyof typeof ui.contextRadar.dimensions] ?? reason.dimension, value: reason.expected })}</small>)}</div></article>)}</div>}
    </section>
  );
}
