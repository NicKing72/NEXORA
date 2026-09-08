"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { createKardexProduct, updateKardexProduct } from "@/lib/kardex-api";
import type { InventoryProduct, ProductDraft } from "@/lib/kardex-types";
import { ui } from "@/lib/i18n";

const emptyProduct = (barcode = ""): ProductDraft => ({
  sku: "", barcode, barcode_type: "EAN13", name: "", description: "", category: "",
  unit_of_measure: "unidad", warehouse: "", supplier: "", valuation_method: "WEIGHTED_AVERAGE",
  forecast_product_reference: "",
  initial_stock: "", initial_unit_cost: "", minimum_stock: "", maximum_stock: "",
});
const number = (value: number | null) => value == null ? "Sin movimientos" : new Intl.NumberFormat("es-PE", { maximumFractionDigits: 4 }).format(value);

export function KardexProducts({
  products,
  suggestedBarcode,
  onCreated,
  onSelect,
}: {
  products: InventoryProduct[];
  suggestedBarcode: string | null;
  onCreated: (product: InventoryProduct) => void;
  onSelect: (product: InventoryProduct) => void;
}) {
  const copy = ui.kardex.products;
  const [showForm, setShowForm] = useState(Boolean(suggestedBarcode));
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<ProductDraft>(() => emptyProduct(suggestedBarcode ?? ""));
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (name: keyof ProductDraft, value: string) => setDraft((current) => ({ ...current, [name]: value }));
  async function submit() {
    setWorking(true); setError(null);
    try {
      const product = editingId
        ? await updateKardexProduct(editingId, draft)
        : await createKardexProduct(draft);
      onCreated(product); setDraft(emptyProduct()); setShowForm(false); setEditingId(null);
    } catch (cause) { setError(cause instanceof Error ? cause.message : ui.kardex.notices.error); }
    finally { setWorking(false); }
  }
  function beginEdit(product: InventoryProduct) {
    setEditingId(product.id);
    setDraft({
      sku: product.sku, barcode: product.barcode ?? "", barcode_type: product.barcode_type ?? "OTHER",
      name: product.name, description: product.description ?? "", category: product.category ?? "",
      unit_of_measure: product.unit_of_measure, warehouse: product.warehouse ?? "",
      supplier: product.supplier ?? "", forecast_product_reference: product.forecast_product_reference ?? "",
      valuation_method: product.valuation_method, initial_stock: "", initial_unit_cost: "",
      minimum_stock: product.minimum_stock == null ? "" : String(product.minimum_stock),
      maximum_stock: product.maximum_stock == null ? "" : String(product.maximum_stock),
    });
    setShowForm(true); setError(null);
  }
  return <div className="kd-stack">
    <section className="kd-panel"><div className="kd-section-head"><div><span>Maestro persistente</span><h2>{copy.title}</h2><p>{copy.subtitle}</p></div><button className="kd-primary" type="button" onClick={() => { setEditingId(null); setDraft(emptyProduct()); setShowForm((value) => !value); }}><Plus size={16} />{copy.new}</button></div>
      {showForm && <div className="kd-product-form">
        <label><span>{copy.sku}</span><input disabled={editingId !== null} value={draft.sku} onChange={(event) => set("sku", event.target.value)} /></label>
        <label><span>{copy.barcode}</span><input value={draft.barcode} onChange={(event) => set("barcode", event.target.value)} /></label>
        <label><span>Formato</span><select value={draft.barcode_type} onChange={(event) => set("barcode_type", event.target.value)}><option>EAN13</option><option>EAN8</option><option>UPC_A</option><option>UPC_E</option><option>CODE128</option><option>QR</option><option>OTHER</option></select></label>
        <label><span>{copy.name}</span><input value={draft.name} onChange={(event) => set("name", event.target.value)} /></label>
        <label><span>{copy.category}</span><input value={draft.category} onChange={(event) => set("category", event.target.value)} /></label>
        <label><span>{copy.unit}</span><input value={draft.unit_of_measure} onChange={(event) => set("unit_of_measure", event.target.value)} /></label>
        <label><span>{copy.warehouse}</span><input value={draft.warehouse} onChange={(event) => set("warehouse", event.target.value)} /></label>
        <label><span>{copy.supplier}</span><input value={draft.supplier} onChange={(event) => set("supplier", event.target.value)} /></label>
        <label><span>Referencia de producto en demanda</span><input placeholder="Ej. NX-101" value={draft.forecast_product_reference} onChange={(event) => set("forecast_product_reference", event.target.value)} /></label>
        <label><span>{copy.method}</span><select value={draft.valuation_method} onChange={(event) => set("valuation_method", event.target.value)}><option value="WEIGHTED_AVERAGE">Promedio ponderado</option><option value="FIFO">PEPS / FIFO</option></select></label>
        {!editingId && <label><span>{copy.initial}</span><input type="number" min="0" step="any" value={draft.initial_stock} onChange={(event) => set("initial_stock", event.target.value)} /></label>}
        {!editingId && <label><span>{copy.initialCost}</span><input type="number" min="0" step="any" value={draft.initial_unit_cost} onChange={(event) => set("initial_unit_cost", event.target.value)} /></label>}
        <label><span>{copy.minimum}</span><input type="number" min="0" step="any" value={draft.minimum_stock} onChange={(event) => set("minimum_stock", event.target.value)} /></label>
        <label><span>{copy.maximum}</span><input type="number" min="0" step="any" value={draft.maximum_stock} onChange={(event) => set("maximum_stock", event.target.value)} /></label>
        <label className="kd-wide"><span>Descripción</span><textarea value={draft.description} onChange={(event) => set("description", event.target.value)} /></label>
        {error && <div className="ds-error-message kd-wide">{error}</div>}
        <div className="kd-form-actions kd-wide"><button className="kd-primary" type="button" disabled={working || !draft.sku || !draft.name} onClick={() => void submit()}>{working ? "Guardando…" : editingId ? "Guardar cambios" : copy.new}</button></div>
      </div>}
    </section>
    <section className="kd-panel"><div className="kd-table-wrap"><table className="kd-product-table"><thead><tr><th>{copy.sku}</th><th>{copy.barcode}</th><th>{copy.name}</th><th>{copy.category}</th><th>{copy.stock}</th><th>{copy.cost}</th><th>{copy.value}</th><th>{copy.method}</th><th>{copy.status}</th><th>Acción</th></tr></thead><tbody>{products.map((product) => <tr key={product.id} onClick={() => onSelect(product)}><td><strong>{product.sku}</strong></td><td>{product.barcode ?? "—"}</td><td>{product.name}</td><td>{product.category ?? "—"}</td><td>{number(product.stock_quantity)}</td><td>{number(product.stock_unit_cost)}</td><td>{number(product.stock_value)}</td><td>{product.valuation_method === "FIFO" ? "PEPS / FIFO" : "Promedio ponderado"}</td><td>{product.active ? copy.active : "Inactivo"}</td><td><button className="kd-table-action" type="button" onClick={(event) => { event.stopPropagation(); beginEdit(product); }}>Editar</button></td></tr>)}</tbody></table></div></section>
  </div>;
}
