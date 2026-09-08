export type ValuationMethod = "FIFO" | "WEIGHTED_AVERAGE";
export type BarcodeType = "EAN13" | "EAN8" | "UPC_A" | "UPC_E" | "CODE128" | "QR" | "OTHER";
export type MovementType =
  | "OPENING_BALANCE" | "PURCHASE_IN" | "PRODUCTION_IN" | "CUSTOMER_RETURN_IN"
  | "TRANSFER_IN" | "SALE_OUT" | "PRODUCTION_CONSUMPTION_OUT"
  | "SUPPLIER_RETURN_OUT" | "TRANSFER_OUT" | "POSITIVE_ADJUSTMENT"
  | "NEGATIVE_ADJUSTMENT";

export type KardexAllocation = {
  inbound_movement_id: string;
  quantity: number;
  unit_cost: number;
  total_cost: number;
};

export type KardexMovement = {
  id: string;
  product_id: string;
  timestamp: string;
  movement_type: MovementType;
  direction: "in" | "out";
  document_reference: string | null;
  warehouse: string | null;
  quantity: number;
  unit_cost: number;
  total_cost: number;
  note: string | null;
  source: "manual" | "barcode" | "import" | "system";
  valuation_method: ValuationMethod;
  balance_quantity: number;
  balance_unit_cost: number;
  balance_total: number;
  created_at: string;
  allocations: KardexAllocation[];
};

export type InventoryProduct = {
  id: string;
  sku: string;
  barcode: string | null;
  barcode_type: BarcodeType | null;
  name: string;
  description: string | null;
  category: string | null;
  unit_of_measure: string;
  warehouse: string | null;
  supplier: string | null;
  forecast_product_reference: string | null;
  active: boolean;
  initial_stock: number | null;
  initial_unit_cost: number | null;
  valuation_method: ValuationMethod;
  minimum_stock: number | null;
  maximum_stock: number | null;
  reorder_reference: number | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  stock_quantity: number | null;
  stock_unit_cost: number | null;
  stock_value: number | null;
  last_movement_at: string | null;
};

export type KardexSummary = {
  active_skus: number;
  units_in_stock: number;
  inventory_value: number;
  out_of_stock: number;
  below_minimum: number;
  movements_today: number;
  inbound_quantity: number;
  outbound_quantity: number;
  latest_movements: KardexMovement[];
};

export type KardexDemo = {
  products: InventoryProduct[];
  summary: KardexSummary;
  demo_barcodes: Record<string, string>;
};

export type ProductDraft = {
  sku: string;
  barcode: string;
  barcode_type: BarcodeType;
  name: string;
  description: string;
  category: string;
  unit_of_measure: string;
  warehouse: string;
  supplier: string;
  forecast_product_reference: string;
  valuation_method: ValuationMethod;
  initial_stock: string;
  initial_unit_cost: string;
  minimum_stock: string;
  maximum_stock: string;
};

export type MovementDraft = {
  product_id: string;
  timestamp: string;
  movement_type: MovementType;
  quantity: string;
  unit_cost: string;
  document_reference: string;
  warehouse: string;
  note: string;
  source: "manual" | "barcode";
};

export type MovementPreview = {
  product_id: string;
  movement_type: MovementType;
  direction: "in" | "out";
  previous_quantity: number;
  movement_quantity: number;
  resulting_quantity: number;
  previous_value: number;
  movement_value: number;
  resulting_value: number;
  effective_unit_cost: number;
  valuation_method: ValuationMethod;
  allocations: KardexAllocation[];
};
