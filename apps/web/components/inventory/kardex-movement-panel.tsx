"use client";

import { CheckCircle2 } from "lucide-react";
import { useState } from "react";

import { createKardexMovement, previewKardexMovement } from "@/lib/kardex-api";
import { isInboundMovement } from "@/lib/kardex-state";
import type { InventoryProduct, KardexMovement, MovementDraft, MovementPreview, MovementType } from "@/lib/kardex-types";
import { ui } from "@/lib/i18n";

const types: MovementType[] = ["PURCHASE_IN", "PRODUCTION_IN", "CUSTOMER_RETURN_IN", "TRANSFER_IN", "SALE_OUT", "PRODUCTION_CONSUMPTION_OUT", "SUPPLIER_RETURN_OUT", "TRANSFER_OUT", "POSITIVE_ADJUSTMENT", "NEGATIVE_ADJUSTMENT"];
const localNow = () => { const date = new Date(); date.setMinutes(date.getMinutes() - date.getTimezoneOffset()); return date.toISOString().slice(0, 16); };
const emptyMovement = (productId = "", source: "manual" | "barcode" = "manual"): MovementDraft => ({ product_id: productId, timestamp: localNow(), movement_type: "PURCHASE_IN", quantity: "", unit_cost: "", document_reference: "", warehouse: "", note: "", source });
const number = (value: number) => new Intl.NumberFormat("es-PE", { maximumFractionDigits: 6 }).format(value);

export function KardexMovementPanel({ products, selected, source = "manual", onCreated }: { products: InventoryProduct[]; selected: InventoryProduct | null; source?: "manual" | "barcode"; onCreated: (movement: KardexMovement) => void }) {
  const copy = ui.kardex.movements;
  const [draft, setDraft] = useState<MovementDraft>(() => ({ ...emptyMovement(selected?.id, source), warehouse: selected?.warehouse ?? "" }));
  const [preview, setPreview] = useState<MovementPreview | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (name: keyof MovementDraft, value: string) => { setDraft((current) => ({ ...current, [name]: value })); setPreview(null); };
  async function prepare() { setWorking(true); setError(null); try { setPreview(await previewKardexMovement({ ...draft, timestamp: new Date(draft.timestamp).toISOString() })); } catch (cause) { setError(cause instanceof Error ? cause.message : ui.kardex.notices.error); } finally { setWorking(false); } }
  async function confirm() { setWorking(true); setError(null); try { const movement = await createKardexMovement({ ...draft, timestamp: new Date(draft.timestamp).toISOString() }); onCreated(movement); setDraft(emptyMovement(draft.product_id, source)); setPreview(null); } catch (cause) { setError(cause instanceof Error ? cause.message : ui.kardex.notices.error); } finally { setWorking(false); } }
  const inbound = isInboundMovement(draft.movement_type);
  return <section className="kd-panel"><div className="kd-section-head"><div><span>Movimiento confirmado y auditable</span><h2>{copy.title}</h2><p>{copy.subtitle}</p></div></div>
    <div className="kd-movement-form">
      <label><span>{copy.product}</span><select value={draft.product_id} onChange={(event) => set("product_id", event.target.value)}><option value="">Selecciona un producto</option>{products.map((product) => <option key={product.id} value={product.id}>{product.sku} · {product.name}</option>)}</select></label>
      <label><span>{copy.type}</span><select value={draft.movement_type} onChange={(event) => set("movement_type", event.target.value)}>{types.map((type) => <option key={type} value={type}>{ui.kardex.movementTypes[type]}</option>)}</select></label>
      <label><span>{copy.timestamp}</span><input type="datetime-local" value={draft.timestamp} onChange={(event) => set("timestamp", event.target.value)} /></label>
      <label><span>{copy.quantity}</span><input type="number" min="0.000001" step="any" value={draft.quantity} onChange={(event) => set("quantity", event.target.value)} /></label>
      {inbound && <label><span>{copy.unitCost}</span><input type="number" min="0" step="any" value={draft.unit_cost} onChange={(event) => set("unit_cost", event.target.value)} /></label>}
      <label><span>{copy.document}</span><input value={draft.document_reference} onChange={(event) => set("document_reference", event.target.value)} /></label>
      <label><span>{copy.warehouse}</span><input value={draft.warehouse} onChange={(event) => set("warehouse", event.target.value)} /></label>
      <label className="kd-wide"><span>{copy.note}</span><textarea value={draft.note} onChange={(event) => set("note", event.target.value)} /></label>
    </div>
    {preview && <div className="kd-preview"><div><span>{copy.previous}</span><strong>{number(preview.previous_quantity)}</strong></div><div><span>{copy.resulting}</span><strong>{number(preview.resulting_quantity)}</strong></div><div><span>{copy.previousValue}</span><strong>{number(preview.previous_value)}</strong></div><div><span>{copy.movementValue}</span><strong>{number(preview.movement_value)}</strong></div><div><span>{copy.resultingValue}</span><strong>{number(preview.resulting_value)}</strong></div><div><span>Método</span><strong>{preview.valuation_method}</strong></div></div>}
    {error && <div className="ds-error-message">{error}</div>}
    <div className="kd-form-actions"><button className="kd-secondary" type="button" disabled={working || !draft.product_id || !draft.quantity || (inbound && draft.unit_cost === "")} onClick={() => void prepare()}>{working ? "Validando…" : ui.kardex.actions.preview}</button><button className="kd-primary" type="button" disabled={working || !preview} onClick={() => void confirm()}><CheckCircle2 size={16} />{ui.kardex.actions.confirm}</button></div>
  </section>;
}
