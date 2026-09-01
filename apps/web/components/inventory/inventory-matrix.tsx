import type { InventoryItem } from "@/lib/inventory-types";
import { ui } from "@/lib/i18n";

const number = (value: number | null) =>
  value == null
    ? ui.inventory.notCalculable
    : new Intl.NumberFormat("es-PE", { maximumFractionDigits: 1 }).format(value);
const timeUnit: Record<string, string> = {
  days: "días",
  weeks: "semanas",
  months: "meses",
};

export function InventoryMatrix({
  items,
  selectedId,
  onSelect,
}: {
  items: InventoryItem[];
  selectedId: string | null;
  onSelect: (item: InventoryItem) => void;
}) {
  const copy = ui.inventory.matrix;
  return (
    <section className="iv-panel">
      <div className="iv-heading"><div><span>{copy.index}</span><h2>{copy.title}</h2></div></div>
      <div className="iv-table-wrap">
        <table className="iv-table">
          <thead><tr><th>{copy.product}</th><th>{copy.forecast}</th><th>{copy.inventory}</th><th>{copy.transit}</th><th>{copy.coverage}</th><th>{copy.leadTime}</th><th>{copy.safety}</th><th>{copy.rop}</th><th>{copy.eoq}</th><th>{copy.balance}</th><th>{copy.recommendation}</th><th>{copy.risk}</th><th>{copy.completeness}</th></tr></thead>
          <tbody>{items.map((item) => (
            <tr key={item.id} className={selectedId === item.id ? "iv-row--selected" : ""} onClick={() => onSelect(item)}>
              <td><strong>{item.product ?? "Todos los productos"}</strong><small>{item.location ?? "Todas las ubicaciones"}</small></td>
              <td>{number(item.forecast_total)}</td><td>{number(item.inventory_on_hand)}</td><td>{number(item.inventory_in_transit)}</td><td>{number(item.physical_coverage)}</td>
              <td>{item.lead_time == null ? "—" : `${number(item.lead_time)} ${timeUnit[item.lead_time_unit ?? ""] ?? item.lead_time_unit ?? ""}`}</td>
              <td>{number(item.safety_stock)}</td><td>{number(item.reorder_point)}</td><td>{number(item.eoq)}</td>
              <td><small>− {number(item.projected_shortage)}</small><small>+ {number(item.projected_surplus)}</small></td>
              <td><strong>{number(item.recommended_quantity)}</strong></td>
              <td><span className={`iv-risk iv-risk--${item.risk_level}`}>{ui.inventory.risk[item.risk_level]}</span></td>
              <td>{item.completeness}%</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </section>
  );
}

