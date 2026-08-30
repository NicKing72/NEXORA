import type { ScorDefinition, ScorMetricResult, ScorProcess } from "@/lib/scor-types";
import { ui } from "@/lib/i18n";

function value(result: ScorMetricResult) {
  if (result.result_value == null) return "—";
  return `${new Intl.NumberFormat("es-PE", { maximumFractionDigits: 2 }).format(result.result_value)} ${result.unit}`;
}

function target(result: ScorMetricResult) {
  if (result.target.direction === "target_range") {
    return `${String(result.target.optional_min ?? "—")} — ${String(result.target.optional_max ?? "—")}`;
  }
  return result.target.target == null ? "—" : String(result.target.target);
}

export function ScorMetricMatrix({ metrics, definitions, process, selectedId, onSelect }: Readonly<{
  metrics: ScorMetricResult[];
  definitions: ScorDefinition[];
  process: ScorProcess | "ALL";
  selectedId: string | null;
  onSelect: (metric: ScorMetricResult) => void;
}>) {
  const copy = ui.scorDiagnostic.matrix;
  const visible = metrics.filter((item) => process === "ALL" || item.process === process);
  const definitionMap = Object.fromEntries(definitions.map((item) => [item.id, item]));
  return (
    <section className="sd-panel">
      <div className="sd-heading"><div><span>{copy.index}</span><h2>{copy.title}</h2></div><strong>{visible.length} KPI</strong></div>
      <div className="sd-table-wrap"><table><thead><tr><th>{copy.process}</th><th>{copy.attribute}</th><th>{copy.kpi}</th><th>{copy.raw}</th><th>{copy.formula}</th><th>{copy.result}</th><th>{copy.evidence}</th><th>{copy.target}</th><th>{copy.gap}</th></tr></thead><tbody>{visible.map((item) => {
        const definition = definitionMap[item.metric_id];
        return <tr key={item.metric_id} className={selectedId === item.metric_id ? "is-selected" : ""} onClick={() => onSelect(item)}><td><b>{item.process}</b></td><td>{ui.scorDiagnostic.attribute[item.attribute as keyof typeof ui.scorDiagnostic.attribute] ?? item.attribute}</td><td><strong>{item.metric_id} · {item.display_name}</strong></td><td>{item.numerator == null && item.denominator == null ? `${definition?.inputs.length ?? 0} campos` : `${item.numerator ?? "—"} / ${item.denominator ?? "—"}`}</td><td><small>{item.formula}</small></td><td><strong>{value(item)}</strong></td><td><span className={`sd-evidence sd-evidence--${item.evidence_status}`}>{ui.scorDiagnostic.evidence[item.evidence_status]}</span></td><td>{target(item)}</td><td>{item.gap_score == null ? "—" : `${item.gap_score.toFixed(1)} / 100`}</td></tr>;
      })}</tbody></table></div>
    </section>
  );
}
