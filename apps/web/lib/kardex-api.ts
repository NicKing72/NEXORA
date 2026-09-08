import { apiRequest } from "@/lib/api-client";
import type {
  InventoryProduct,
  KardexDemo,
  KardexMovement,
  KardexSummary,
  MovementDraft,
  MovementPreview,
  ProductDraft,
} from "@/lib/kardex-types";

const API_ORIGIN = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const optionalNumber = (value: string) => value === "" ? null : Number(value);
const optionalText = (value: string) => value.trim() || null;

export const listKardexProducts = (query = "") => apiRequest<InventoryProduct[]>(
  `/api/v1/kardex/products${query ? `?query=${encodeURIComponent(query)}` : ""}`,
);
export const lookupKardexProduct = (identifier: string) => apiRequest<InventoryProduct>(
  `/api/v1/kardex/products/lookup?identifier=${encodeURIComponent(identifier)}`,
);
export const createKardexProduct = (draft: ProductDraft) => apiRequest<InventoryProduct>(
  "/api/v1/kardex/products",
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sku: draft.sku,
      barcode: optionalText(draft.barcode),
      barcode_type: draft.barcode ? draft.barcode_type : null,
      name: draft.name,
      description: optionalText(draft.description),
      category: optionalText(draft.category),
      unit_of_measure: draft.unit_of_measure,
      warehouse: optionalText(draft.warehouse),
      supplier: optionalText(draft.supplier),
      forecast_product_reference: optionalText(draft.forecast_product_reference),
      valuation_method: draft.valuation_method,
      initial_stock: optionalNumber(draft.initial_stock),
      initial_unit_cost: optionalNumber(draft.initial_unit_cost),
      minimum_stock: optionalNumber(draft.minimum_stock),
      maximum_stock: optionalNumber(draft.maximum_stock),
    }),
  },
);
export const updateKardexProduct = (id: string, draft: ProductDraft) => apiRequest<InventoryProduct>(
  `/api/v1/kardex/products/${id}`,
  {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      barcode: optionalText(draft.barcode),
      barcode_type: draft.barcode ? draft.barcode_type : null,
      name: draft.name,
      description: optionalText(draft.description),
      category: optionalText(draft.category),
      unit_of_measure: draft.unit_of_measure,
      warehouse: optionalText(draft.warehouse),
      supplier: optionalText(draft.supplier),
      forecast_product_reference: optionalText(draft.forecast_product_reference),
      minimum_stock: optionalNumber(draft.minimum_stock),
      maximum_stock: optionalNumber(draft.maximum_stock),
    }),
  },
);
export const listProductMovements = (productId: string) => apiRequest<KardexMovement[]>(
  `/api/v1/kardex/products/${productId}/movements`,
);
export const getKardexSummary = () => apiRequest<KardexSummary>("/api/v1/kardex/summary");
export const regenerateKardexDemo = () => apiRequest<KardexDemo>(
  "/api/v1/kardex/demo/regenerate",
  { method: "POST" },
);

function movementBody(draft: MovementDraft) {
  return {
    ...draft,
    quantity: Number(draft.quantity),
    unit_cost: draft.unit_cost === "" ? null : Number(draft.unit_cost),
    document_reference: optionalText(draft.document_reference),
    warehouse: optionalText(draft.warehouse),
    note: optionalText(draft.note),
  };
}

export const previewKardexMovement = (draft: MovementDraft) => apiRequest<MovementPreview>(
  "/api/v1/kardex/movements/preview",
  { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(movementBody(draft)) },
);
export const createKardexMovement = (draft: MovementDraft) => apiRequest<KardexMovement>(
  "/api/v1/kardex/movements",
  { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(movementBody(draft)) },
);

export function kardexExportUrl(productId?: string): string {
  const query = productId ? `?product_id=${encodeURIComponent(productId)}` : "";
  return `${API_ORIGIN}/api/v1/kardex/export.xlsx${query}`;
}
