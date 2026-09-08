import { ArrowDownToLine, ArrowUpFromLine, Boxes, PackageX } from "lucide-react";

import type { InventoryProduct, KardexSummary } from "@/lib/kardex-types";
import { ui } from "@/lib/i18n";

const quantity = (value: number) => new Intl.NumberFormat("es-PE", { maximumFractionDigits: 2 }).format(value);
const money = (value: number) => new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN", maximumFractionDigits: 2 }).format(value);

export function KardexSummaryView({
  summary,
  products,
  onSelect,
}: {
  summary: KardexSummary | null;
  products: InventoryProduct[];
  onSelect: (product: InventoryProduct) => void;
}) {
  const copy = ui.kardex.summary;
  if (!summary) return <section className="kd-panel kd-empty">{ui.kardex.notices.missingIsNotZero}</section>;
  const productMap = new Map(products.map((product) => [product.id, product]));
  const metrics = [
    [copy.active, summary.active_skus, Boxes],
    [copy.units, quantity(summary.units_in_stock), Boxes],
    [copy.value, money(summary.inventory_value), Boxes],
    [copy.noStock, summary.out_of_stock, PackageX],
    [copy.belowMinimum, summary.below_minimum, PackageX],
    [copy.today, summary.movements_today, Boxes],
    [copy.inbound, quantity(summary.inbound_quantity), ArrowDownToLine],
    [copy.outbound, quantity(summary.outbound_quantity), ArrowUpFromLine],
  ] as const;
  return (
    <div className="kd-stack">
      <section className="kd-kpis">
        {metrics.map(([label, value, Icon]) => <article key={label}><Icon size={16} /><span>{label}</span><strong>{value}</strong></article>)}
      </section>
      <section className="kd-panel">
        <div className="kd-section-head"><div><span>Actividad reciente</span><h2>{copy.recent}</h2></div></div>
        {summary.latest_movements.length ? <div className="kd-recent-list">{summary.latest_movements.map((movement) => {
          const product = productMap.get(movement.product_id);
          return <button type="button" key={movement.id} onClick={() => product && onSelect(product)}><span><strong>{product?.sku ?? movement.product_id.slice(0, 8)} · {ui.kardex.movementTypes[movement.movement_type]}</strong><small>{new Date(movement.timestamp).toLocaleString("es-PE")} · {movement.document_reference ?? "Sin documento"}</small></span><b className={movement.direction === "in" ? "kd-in" : "kd-out"}>{movement.direction === "in" ? "+" : "−"}{quantity(movement.quantity)}</b></button>;
        })}</div> : <p className="kd-muted">Aún no existen movimientos confirmados.</p>}
      </section>
    </div>
  );
}
