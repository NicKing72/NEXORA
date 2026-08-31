import type { PortfolioItem } from "@/lib/portfolio-types";
import { translateFrequency, ui } from "@/lib/i18n";

function number(value: number | null, digits = 1) {
  return value == null ? "—" : new Intl.NumberFormat("es-PE", { maximumFractionDigits: digits }).format(value);
}

export function PortfolioMatrix({ items, selectedId, onSelect }: {
  items: PortfolioItem[];
  selectedId: string | null;
  onSelect: (item: PortfolioItem) => void;
}) {
  const copy = ui.portfolio;
  return (
    <section className="pf-panel">
      <div className="pf-heading"><div><span>{copy.matrix.index}</span><h2>{copy.matrix.title}</h2></div><small>{items.length} {copy.matrix.series}</small></div>
      <div className="pf-table-wrap">
        <table className="pf-table">
          <thead><tr><th>{copy.matrix.priority}</th><th>{copy.matrix.product}</th><th>{copy.matrix.location}</th><th>{copy.matrix.category}</th><th>Champion</th><th>{copy.matrix.forecast}</th><th>{copy.matrix.peak}</th><th>{copy.matrix.coverage}</th><th>{copy.matrix.data}</th><th>{copy.matrix.risk}</th><th>Score</th></tr></thead>
          <tbody>{items.map((item) => <tr key={item.id} className={selectedId === item.id ? "pf-row--selected" : ""} onClick={() => onSelect(item)} tabIndex={0} onKeyDown={(event) => { if (event.key === "Enter") onSelect(item); }}><td><span className={`pf-rank pf-risk--${item.risk_level}`}>#{item.rank}</span></td><td><strong>{item.product ?? copy.allProducts}</strong><small>{translateFrequency(item.forecast_frequency)}</small></td><td>{item.location ?? copy.allLocations}</td><td>{item.category ?? "—"}</td><td>{item.champion}</td><td>{number(item.forecast_total)}</td><td>{number(item.forecast_peak)}</td><td>{item.inventory_coverage == null ? copy.notCalculable : `${number(item.inventory_coverage)} ${copy.periods[item.forecast_frequency as keyof typeof copy.periods] ?? copy.periods.default}`}</td><td><span className={`pf-data pf-data--${item.operational_data_completeness}`}>{copy.completeness[item.operational_data_completeness]}</span></td><td><span className={`pf-risk pf-risk--${item.risk_level}`}>{copy.risks[item.risk_level]}</span></td><td><strong>{number(item.priority_score)}</strong><small>{item.score_status === "partial" ? copy.partialScore : copy.completeScore}</small></td></tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}
