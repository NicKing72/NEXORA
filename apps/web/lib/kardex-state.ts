import type { MovementType } from "@/lib/kardex-types";

export type InventorySection = "summary" | "kardex" | "movements" | "products" | "replenishment";

const inbound = new Set<MovementType>([
  "OPENING_BALANCE", "PURCHASE_IN", "PRODUCTION_IN", "CUSTOMER_RETURN_IN",
  "TRANSFER_IN", "POSITIVE_ADJUSTMENT",
]);

export function isInboundMovement(type: MovementType): boolean {
  return inbound.has(type);
}

export function inventorySectionFromSearch(search: string): InventorySection {
  const value = new URLSearchParams(search).get("view");
  if (value === "kardex" || value === "movements" || value === "products" || value === "replenishment") {
    return value;
  }
  return new URLSearchParams(search).has("inventory_run_id") ? "replenishment" : "summary";
}

export function inventoryProductIdFromSearch(search: string): string | null {
  return new URLSearchParams(search).get("product_id");
}

export function stopMediaStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop());
}
