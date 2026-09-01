import { Calculator, ShieldAlert } from "lucide-react";

import type { InventoryItem, InventoryRun } from "@/lib/inventory-types";
import { ui } from "@/lib/i18n";

const number = (value: number | null) => value == null
  ? ui.inventory.notCalculable
  : new Intl.NumberFormat("es-PE", { maximumFractionDigits: 2 }).format(value);
const calculationLabels: Record<string, string> = {
  physical_coverage: "Cobertura física", coverage_with_transit: "Cobertura con tránsito",
  lead_time_demand: "Demanda durante lead time", safety_stock: "Stock de seguridad",
  reorder_point: "Punto de reorden", eoq: "EOQ", net_requirement: "Necesidad neta",
};
const constraintLabels: Record<string, string> = {
  moq: "MOQ", lot_multiple: "Múltiplo de compra", capacity: "Capacidad máxima",
};

export function InventoryDetail({ item, run }: { item: InventoryItem | null; run: InventoryRun }) {
  const copy = ui.inventory.detail;
  if (!item) return <section className="iv-panel iv-empty">{ui.inventory.matrix.select}</section>;
  const metrics: Array<[string, number | null]> = [
    ["Pronóstico total", item.forecast_total], ["Promedio por periodo", item.forecast_average],
    ["Cobertura física", item.physical_coverage], ["Cobertura con tránsito", item.coverage_with_transit],
    ["Demanda durante lead time", item.lead_time_demand], ["Stock de seguridad", item.safety_stock],
    ["Punto de reorden", item.reorder_point], ["EOQ", item.eoq],
    ["Necesidad neta", item.raw_requirement], ["Cantidad propuesta", item.recommended_quantity],
  ];
  const explanations: Array<[string, unknown]> = [
    [copy.detected, item.explanation.detected], [copy.importance, item.explanation.why_it_matters],
    [copy.used, item.explanation.data_used],
    [copy.missing, item.missing_inputs.length ? item.missing_inputs.map((name) => ui.inventory.inputs[name as keyof typeof ui.inventory.inputs] ?? name).join(", ") : "Sin faltantes críticos declarados"],
    [copy.review, item.explanation.review], [copy.cannot, item.explanation.cannot_conclude],
  ];
  return (
    <section className="iv-detail-grid">
      <article className="iv-panel">
        <div className="iv-heading"><div><span>{copy.index}</span><h2>{copy.title}</h2></div><Calculator size={18} /></div>
        <div className="iv-metrics">{metrics.map(([label, value]) => <div key={label}><span>{label}</span><strong>{number(value)}</strong></div>)}</div>
        <div className="iv-formulas"><h3>{copy.formulas}</h3>{Object.entries(item.calculations).map(([key, calc]) => (
          <details key={key}><summary>{calculationLabels[key] ?? key} · {calc.status === "calculated" ? number(calc.result) : ui.inventory.notCalculable}</summary><code>{calc.formula}</code>{calc.substitution && <p>{calc.substitution}</p>}{calc.reason && <small>{calc.reason.replaceAll("_", " ")}</small>}</details>
        ))}</div>
      </article>
      <article className="iv-panel iv-explain">
        <div className="iv-heading"><div><span>Evidencia</span><h2>Lectura operacional</h2></div><ShieldAlert size={18} /></div>
        {explanations.map(([label, value]) => <div key={label}><span>{label}</span><p>{String(value ?? "—")}</p></div>)}
        <div><span>{copy.constraints}</span><p>{item.constraints.length ? item.constraints.map((constraint) => constraintLabels[String(constraint.type)] ?? String(constraint.type)).join(" · ") : "Sin restricciones aplicadas"}</p></div>
        <div><span>{copy.provenance}</span><p>Run {run.id} · {run.calculation_version} · cutoff {new Date(run.cutoff).toLocaleString("es-PE")}</p></div>
      </article>
    </section>
  );
}
