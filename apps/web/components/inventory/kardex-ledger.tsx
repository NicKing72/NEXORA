import { Download } from "lucide-react";

import { kardexExportUrl } from "@/lib/kardex-api";
import type { InventoryProduct, KardexMovement } from "@/lib/kardex-types";
import { ui } from "@/lib/i18n";

const number = (value: number) => new Intl.NumberFormat("es-PE", { maximumFractionDigits: 6 }).format(value);
const money = (value: number) => new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN", maximumFractionDigits: 2 }).format(value);

export function KardexLedger({ product, movements }: { product: InventoryProduct | null; movements: KardexMovement[] }) {
  const copy = ui.kardex.ledger;
  return <section className="kd-panel">
    <div className="kd-section-head"><div><span>{product ? `${product.sku} · ${product.valuation_method}` : "Trazabilidad por SKU"}</span><h2>{copy.title}</h2><p>{copy.subtitle}</p></div>{product && <a className="kd-secondary" href={kardexExportUrl(product.id)}><Download size={16} />{ui.kardex.actions.export}</a>}</div>
    {!product || !movements.length ? <p className="kd-empty">{copy.empty}</p> : <div className="kd-table-wrap"><table className="kd-ledger-table"><thead><tr><th>{copy.date}</th><th>{copy.document}</th><th>{copy.movement}</th><th>{copy.input} · cantidad</th><th>{copy.input} · costo</th><th>{copy.input} · total</th><th>{copy.output} · cantidad</th><th>{copy.output} · costo</th><th>{copy.output} · total</th><th>{copy.balance}</th><th>{copy.balanceCost}</th><th>{copy.balanceValue}</th><th>Método</th><th>{copy.source}</th><th>{copy.note}</th></tr></thead><tbody>{[...movements].reverse().map((movement) => <tr key={movement.id}><td>{new Date(movement.timestamp).toLocaleString("es-PE")}</td><td>{movement.document_reference ?? "—"}</td><td><strong>{ui.kardex.movementTypes[movement.movement_type]}</strong>{movement.allocations.length > 0 && <small>{copy.allocations}: {movement.allocations.map((item) => `${number(item.quantity)} @ ${money(item.unit_cost)}`).join(" · ")}</small>}</td><td className="kd-in">{movement.direction === "in" ? number(movement.quantity) : "—"}</td><td>{movement.direction === "in" ? money(movement.unit_cost) : "—"}</td><td>{movement.direction === "in" ? money(movement.total_cost) : "—"}</td><td className="kd-out">{movement.direction === "out" ? number(movement.quantity) : "—"}</td><td>{movement.direction === "out" ? money(movement.unit_cost) : "—"}</td><td>{movement.direction === "out" ? money(movement.total_cost) : "—"}</td><td>{number(movement.balance_quantity)}</td><td>{money(movement.balance_unit_cost)}</td><td>{money(movement.balance_total)}</td><td>{movement.valuation_method === "FIFO" ? "PEPS" : "Promedio"}</td><td>{movement.source}</td><td>{movement.note ?? "—"}</td></tr>)}</tbody></table></div>}
  </section>;
}
