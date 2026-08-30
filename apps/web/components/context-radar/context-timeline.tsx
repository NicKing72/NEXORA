import { CalendarDays, Clock3 } from "lucide-react";

import type { ContextSignal, SignalFamily } from "@/lib/context-types";
import { interpolate, ui } from "@/lib/i18n";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-PE", { dateStyle: "medium" }).format(new Date(value));
}

function bucket(signal: ContextSignal, referenceTime: number): "past" | "today" | "future" {
  const now = new Date(referenceTime);
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const end = start + 86_400_000 - 1;
  const signalStart = new Date(signal.event_start).getTime();
  const signalEnd = new Date(signal.event_end ?? signal.event_start).getTime();
  if (signalEnd < start) return "past";
  if (signalStart > end) return "future";
  return "today";
}

type Props = { signals: ContextSignal[]; selectedId: string | null; referenceTime: number; onSelect: (signal: ContextSignal) => void };

export function ContextTimeline({ signals, selectedId, referenceTime, onSelect }: Readonly<Props>) {
  const copy = ui.contextRadar.timeline;
  const groups = (["past", "today", "future"] as const).map((name) => ({ name, signals: signals.filter((item) => bucket(item, referenceTime) === name) }));
  return (
    <section className="cx-panel cx-timeline" aria-labelledby="cx-timeline-title">
      <div className="cx-heading"><div><span className="section-index">{copy.index}</span><h2 id="cx-timeline-title">{copy.title}</h2><p>{copy.subtitle}</p></div><CalendarDays size={19} /></div>
      {signals.length === 0 ? <div className="cx-empty-inline">{copy.noSignals}</div> : (
        <div className="cx-timeline-grid">
          {groups.map((group) => <div className={`cx-era cx-era--${group.name}`} key={group.name}>
            <div className="cx-era-heading"><span>{copy[group.name]}</span><strong>{group.signals.length}</strong></div>
            <div className="cx-era-track">{group.signals.map((signal) => (
              <button type="button" className={`cx-signal-card${selectedId === signal.id ? " cx-signal-card--selected" : ""}`} data-family={signal.signal_family} key={signal.id} onClick={() => onSelect(signal)}>
                <span className="cx-family-mark" /><small>{ui.contextRadar.families[signal.signal_family as SignalFamily]}</small><strong>{signal.title}</strong><time>{formatDate(signal.event_start)}</time><span className="cx-available"><Clock3 size={11} />{interpolate(copy.available, { date: formatDate(signal.available_at) })}</span>{signal.confidence !== null && <i>{interpolate(copy.confidence, { value: Math.round(signal.confidence * 100) })}</i>}
              </button>
            ))}</div>
          </div>)}
        </div>
      )}
    </section>
  );
}
