import { CalendarClock, CircleCheck, Eye, ShieldCheck } from "lucide-react";

import type { ContextSignal } from "@/lib/context-types";
import { ui } from "@/lib/i18n";

export function ContextSummary({ signals, referenceTime }: Readonly<{ signals: ContextSignal[]; referenceTime: number }>) {
  const metrics = [
    { label: ui.contextRadar.summary.active, value: signals.filter((item) => !["dismissed", "expired"].includes(item.status)).length, icon: CircleCheck },
    { label: ui.contextRadar.summary.future, value: signals.filter((item) => item.knowledge_type === "known_future" && new Date(item.event_start).getTime() > referenceTime).length, icon: CalendarClock },
    { label: ui.contextRadar.summary.review, value: signals.filter((item) => ["detected", "reviewed"].includes(item.status)).length, icon: Eye },
    { label: ui.contextRadar.summary.confidence, value: signals.filter((item) => (item.confidence ?? 0) >= 0.8).length, icon: ShieldCheck },
  ];
  return (
    <section className="cx-summary" aria-label={ui.contextRadar.summary.auditNote}>
      {metrics.map(({ label, value, icon: Icon }) => (
        <div key={label}><Icon size={16} /><span><small>{label}</small><strong>{value}</strong></span></div>
      ))}
      <p>{ui.contextRadar.summary.auditNote}</p>
    </section>
  );
}
