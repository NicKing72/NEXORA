import { Clock3 } from "lucide-react";

import { ui } from "@/lib/i18n";
import type { ReportRunSummary } from "@/lib/report-types";

export function ReportHistory({ items, selectedId, onSelect }: Readonly<{ items: ReportRunSummary[]; selectedId: string | null; onSelect: (id: string) => void }>) {
  const copy = ui.reports.history;
  return <section className="rp-panel rp-history"><div className="rp-section-heading"><div><span>{copy.index}</span><h2>{copy.title}</h2></div><Clock3 size={17} /></div>{items.length === 0 ? <p>{copy.empty}</p> : <div className="rp-history-list">{items.map((item) => <button type="button" key={item.id} className={item.id === selectedId ? "is-active" : ""} onClick={() => onSelect(item.id)}><span><strong>{item.title}</strong><small>{new Date(item.created_at).toLocaleString("es-PE")} · {ui.reports.types[item.report_type]} · {String(item.scope.product ?? "Serie agregada")} · {String(item.scope.location ?? "Todas")}</small></span><span><strong>{copy.layers.replace("{count}", String(item.layer_count))}</strong><small>{copy.warnings.replace("{count}", String(item.warning_count))} · {item.id.slice(0, 8)}</small></span></button>)}</div>}</section>;
}
