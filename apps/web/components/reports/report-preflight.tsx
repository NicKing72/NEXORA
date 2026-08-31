import { CheckCircle2, Layers3 } from "lucide-react";

import { ui } from "@/lib/i18n";
import type { ReportPreflight } from "@/lib/report-types";

export function ReportPreflightPanel({ preflight }: Readonly<{ preflight: ReportPreflight }>) {
  const copy = ui.reports.preflight;
  return (
    <section className="rp-panel rp-preflight">
      <div className="rp-section-heading"><div><span>{copy.index}</span><h2>{copy.title}</h2></div><strong className="rp-ready"><CheckCircle2 size={15} />{copy.ready}</strong></div>
      <div className="rp-preflight-summary">
        <div><small>{copy.coverage}</small><strong>{copy.included.replace("{count}", String(preflight.coverage.included)).replace("{total}", String(preflight.coverage.total))}</strong></div>
        <div><small>{copy.cutoff}</small><strong>{new Date(preflight.report_cutoff).toLocaleString("es-PE")}</strong></div>
      </div>
      <div className="rp-layer-grid">{Object.entries(preflight.sources).map(([key, source]) => <div key={key} className={source.included ? "is-included" : "is-missing"}><Layers3 size={15} /><span><strong>{ui.reports.layers[key as keyof typeof ui.reports.layers] ?? key}</strong><small>{source.included ? copy.available : copy.unavailable}</small></span></div>)}</div>
      <p className="rp-contract-note">{copy.warning}</p>
      {(preflight.warnings.length > 0 || preflight.limitations.length > 0) && <div className="rp-preflight-notes">
        {preflight.warnings.length > 0 && <div><strong>{copy.warnings}</strong><ul>{preflight.warnings.map((item) => <li key={item}>{item.replace("source_not_included:", "No incluida: ")}</li>)}</ul></div>}
        {preflight.limitations.length > 0 && <div><strong>{copy.limitations}</strong><ul>{preflight.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div>}
      </div>}
    </section>
  );
}
