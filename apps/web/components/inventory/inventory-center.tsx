"use client";

import { Barcode, Boxes, ClipboardList, PackagePlus, RefreshCw, Search, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { BarcodeScanner } from "@/components/inventory/barcode-scanner";
import { DemoBarcodes } from "@/components/inventory/demo-barcodes";
import { InventoryWorkspace } from "@/components/inventory/inventory-workspace";
import { KardexLedger } from "@/components/inventory/kardex-ledger";
import { KardexMovementPanel } from "@/components/inventory/kardex-movement-panel";
import { KardexProducts } from "@/components/inventory/kardex-products";
import { KardexSummaryView } from "@/components/inventory/kardex-summary";
import {
  getKardexSummary,
  listKardexProducts,
  listProductMovements,
  lookupKardexProduct,
  regenerateKardexDemo,
} from "@/lib/kardex-api";
import { inventoryProductIdFromSearch, inventorySectionFromSearch, type InventorySection } from "@/lib/kardex-state";
import type { InventoryProduct, KardexMovement, KardexSummary } from "@/lib/kardex-types";
import { ui } from "@/lib/i18n";

const tabs: InventorySection[] = ["summary", "kardex", "movements", "products", "replenishment"];

export function InventoryCenter() {
  const copy = ui.kardex;
  const [section, setSection] = useState<InventorySection>("summary");
  const [products, setProducts] = useState<InventoryProduct[]>([]);
  const [summary, setSummary] = useState<KardexSummary | null>(null);
  const [selected, setSelected] = useState<InventoryProduct | null>(null);
  const [movements, setMovements] = useState<KardexMovement[]>([]);
  const [query, setQuery] = useState("");
  const [unknownBarcode, setUnknownBarcode] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (preferredId?: string) => {
    const [productItems, currentSummary] = await Promise.all([listKardexProducts(), getKardexSummary()]);
    setProducts(productItems);
    setSummary(currentSummary);
    const product = productItems.find((item) => item.id === (preferredId ?? selected?.id)) ?? null;
    setSelected(product);
    setMovements(product ? await listProductMovements(product.id) : []);
  }, [selected?.id]);

  useEffect(() => {
    let active = true;
    Promise.all([listKardexProducts(), getKardexSummary()])
      .then(async ([productItems, currentSummary]) => {
        if (!active) return;
        const requestedProductId = inventoryProductIdFromSearch(window.location.search);
        const requestedProduct = requestedProductId
          ? productItems.find((product) => product.id === requestedProductId) ?? null
          : null;
        const requestedMovements = requestedProduct
          ? await listProductMovements(requestedProduct.id)
          : [];
        if (!active) return;
        setProducts(productItems);
        setSummary(currentSummary);
        setSelected(requestedProduct);
        setMovements(requestedMovements);
        setSection(inventorySectionFromSearch(window.location.search));
        if (requestedProductId && !requestedProduct) {
          setError("El producto solicitado no existe o ya no está disponible.");
        }
      })
      .catch((cause: Error) => active && setError(cause.message))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  const navigate = useCallback((next: InventorySection, productId?: string | null) => {
    const resolvedProductId = productId === undefined ? selected?.id ?? null : productId;
    setSection(next);
    const params = new URLSearchParams(window.location.search);
    params.set("view", next);
    if (next !== "replenishment") params.delete("inventory_run_id");
    if (resolvedProductId) params.set("product_id", resolvedProductId);
    else params.delete("product_id");
    window.history.replaceState(null, "", `/inventory?${params.toString()}`);
  }, [selected?.id]);

  const selectProduct = useCallback(async (product: InventoryProduct, next: InventorySection = "kardex") => {
    setSelected(product); setUnknownBarcode(null); setError(null);
    setMovements(await listProductMovements(product.id));
    navigate(next, product.id);
  }, [navigate]);

  const locate = useCallback(async (value: string) => {
    const normalized = value.trim();
    if (!normalized) return;
    setWorking(true); setError(null);
    try { await selectProduct(await lookupKardexProduct(normalized)); }
    catch (cause) {
      setUnknownBarcode(normalized);
      setSelected(null); setMovements([]);
      setError(cause instanceof Error ? cause.message : copy.notices.error);
    } finally { setWorking(false); }
  }, [copy.notices.error, selectProduct]);

  async function demo() {
    setWorking(true); setError(null);
    try {
      const result = await regenerateKardexDemo();
      setProducts(result.products); setSummary(result.summary);
      const beverage = result.products.find((product) => product.sku === "BEB-001") ?? result.products[0];
      if (beverage) await selectProduct(beverage, "kardex");
    } catch (cause) { setError(cause instanceof Error ? cause.message : copy.notices.error); }
    finally { setWorking(false); }
  }

  async function movementCreated() {
    await refresh(selected?.id);
    navigate("kardex");
  }

  if (loading) return <div className="workspace kd-workspace"><div className="kd-loading"><RefreshCw size={18} />{copy.notices.loading}</div></div>;
  return <div className="workspace kd-workspace">
    <header className="workspace-header kd-header"><div><span className="eyebrow">{copy.header.eyebrow}</span><h1>{copy.header.title}</h1><p>{copy.header.subtitle}</p></div><div className="kd-boundaries"><span><ShieldCheck size={15} />{copy.header.audit}</span><span><Barcode size={15} />{copy.header.localCamera}</span></div></header>
    <nav className="kd-tabs" aria-label="Secciones de inventario">{tabs.map((tab) => <button key={tab} type="button" className={section === tab ? "active" : ""} onClick={() => navigate(tab)}>{copy.tabs[tab]}</button>)}</nav>
    {section !== "replenishment" && <section className="kd-toolbar"><label><span>{copy.search.label}</span><div><Search size={17} /><input value={query} placeholder={copy.search.placeholder} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void locate(query); }} /><button type="button" disabled={working} onClick={() => void locate(query)}>Buscar</button></div></label><div className="kd-toolbar-actions"><BarcodeScanner onDetected={(value) => { setQuery(value); void locate(value); }} /><button className="kd-secondary" type="button" disabled={working} onClick={() => void demo()}><RefreshCw size={16} />{copy.actions.demo}</button></div></section>}
    {error && <div className="ds-error-message">{error}</div>}
    {unknownBarcode && <section className="kd-unknown"><Barcode size={22} /><div><strong>{copy.search.unknown}</strong><span>{unknownBarcode}</span></div><button className="kd-primary" type="button" onClick={() => navigate("products")}><PackagePlus size={16} />{copy.search.create}</button></section>}
    {selected && section !== "products" && section !== "replenishment" && <section className="kd-product-hit"><div><span>{copy.search.found}</span><h2>{selected.sku} · {selected.name}</h2><p>{selected.barcode ?? "Sin código"} · Stock {selected.stock_quantity ?? "sin movimientos"} · {selected.valuation_method === "FIFO" ? "PEPS / FIFO" : "Promedio ponderado"}</p></div><div><button type="button" onClick={() => navigate("movements")}><PackagePlus size={15} />{copy.actions.entry}</button><button type="button" onClick={() => navigate("kardex")}><ClipboardList size={15} />{copy.actions.ledger}</button><button type="button" onClick={() => navigate("replenishment")}><Boxes size={15} />{copy.actions.replenish}</button></div></section>}
    {section === "summary" && <><KardexSummaryView summary={summary} products={products} onSelect={(product) => void selectProduct(product)} /><DemoBarcodes products={products} /></>}
    {section === "kardex" && <KardexLedger product={selected} movements={movements} />}
    {section === "movements" && <KardexMovementPanel key={`${selected?.id ?? "none"}:${query && selected?.barcode === query ? "barcode" : "manual"}`} products={products} selected={selected} source={query && selected?.barcode === query ? "barcode" : "manual"} onCreated={() => void movementCreated()} />}
    {section === "products" && <KardexProducts key={unknownBarcode ?? "products"} products={products} suggestedBarcode={unknownBarcode} onCreated={(product) => { setUnknownBarcode(null); void refresh(product.id); }} onSelect={(product) => void selectProduct(product)} />}
    {section === "replenishment" && <InventoryWorkspace initialKardexProductId={selected?.id ?? null} />}
  </div>;
}
