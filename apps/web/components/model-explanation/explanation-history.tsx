import type { ExplanationRunSummary } from "@/lib/explanation-types";
import { ui } from "@/lib/i18n";

export function ExplanationHistory({ items, selectedId, onSelect }: Readonly<{ items: ExplanationRunSummary[]; selectedId: string | null; onSelect: (id: string) => void }>) {
  const copy = ui.modelExplanation.history;
  return (
    <section className="mx-panel mx-history">
      <div className="mx-section-heading"><div><span>{copy.index}</span><h2>{copy.title}</h2></div></div>
      {items.length === 0 ? <p>{copy.empty}</p> : <div className="mx-history-list">{items.map((item) => <button type="button" key={item.id} className={selectedId === item.id ? "is-selected" : ""} onClick={() => onSelect(item.id)}><span><strong>{new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.created_at))}</strong><small>{item.forecast_run_id}</small></span><span>{ui.forecastLab.modelNames[item.champion_model as keyof typeof ui.forecastLab.modelNames] ?? item.champion_model}<small>{item.frequency} · {item.horizon} periodos</small></span></button>)}</div>}
    </section>
  );
}
