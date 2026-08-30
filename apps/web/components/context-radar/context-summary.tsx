import { Activity, CircleCheck, History, ShieldAlert } from "lucide-react";

import type { ContextAnalogy, ContextImpactEstimate, ContextSignal } from "@/lib/context-types";
import { ui } from "@/lib/i18n";

type Props = {
  signals: ContextSignal[];
  impacts: ContextImpactEstimate[];
  analogies: ContextAnalogy[];
};

export function ContextSummary({ signals, impacts, analogies }: Readonly<Props>) {
  const metrics = [
    { label: ui.contextRadar.summary.active, value: signals.filter((item) => !["dismissed", "expired"].includes(item.status)).length, icon: CircleCheck },
    { label: ui.contextRadar.summary.estimated, value: impacts.filter((item) => item.status === "estimated").length, icon: Activity },
    { label: ui.contextRadar.summary.insufficient, value: impacts.filter((item) => item.status !== "estimated").length, icon: ShieldAlert },
    { label: ui.contextRadar.summary.analogies, value: analogies.filter((item) => item.status === "available").length, icon: History },
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
