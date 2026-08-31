import { FileCheck2, ShieldCheck } from "lucide-react";

import { ui } from "@/lib/i18n";

export function ReportHeader() {
  const copy = ui.reports.header;
  return (
    <header className="rp-header">
      <div>
        <span className="eyebrow">{copy.eyebrow}</span>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
      </div>
      <div className="rp-header-badges">
        <span><FileCheck2 size={15} />{copy.auditable}</span>
        <span><ShieldCheck size={15} />{copy.noRecalculation}</span>
      </div>
    </header>
  );
}
