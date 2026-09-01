import type { ForecastRunSummary, ScenarioRunSummary } from "@/lib/scenario-types";
import type { PortfolioRun, PortfolioRunSummary } from "@/lib/portfolio-types";

export type { ForecastRunSummary, PortfolioRun, PortfolioRunSummary, ScenarioRunSummary };

export type InventoryInputName =
  | "inventory_on_hand" | "inventory_in_transit" | "safety_stock" | "lead_time"
  | "service_level" | "unit_cost" | "order_cost" | "holding_cost" | "holding_rate"
  | "moq" | "lot_multiple" | "capacity" | "committed_inventory" | "backorders";

export type InventoryDraft = Record<InventoryInputName, string>;

export type InventoryPreflight = {
  forecast_run_id: string; dataset_id: string; scenario_run_id: string | null;
  portfolio_run_id: string | null; decision_run_id: string | null; cutoff: string;
  product: string | null; location: string | null; category: string | null;
  frequency: string; horizon: number; champion: string; demand_source: string;
  available_inputs: string[]; missing_inputs: string[]; calculable: Record<string, boolean>;
  readiness: "ready" | "warning" | "blocked"; warnings: string[];
};

export type InventoryCalculation = {
  formula: string; substitution: string | null; result: number | null; unit: string;
  status: string; reason: string | null;
};

export type InventoryItem = {
  id: string; forecast_run_id: string | null; product: string | null; location: string | null;
  category: string | null; frequency: string; horizon: number; demand_source: string;
  forecast_total: number; forecast_average: number; inventory_on_hand: number | null;
  inventory_in_transit: number | null; safety_stock: number | null;
  safety_stock_source: string | null; lead_time: number | null; lead_time_unit: string | null;
  service_level: number | null; unit_cost: number | null; order_cost: number | null;
  holding_cost: number | null; moq: number | null; capacity: number | null;
  physical_coverage: number | null; coverage_with_transit: number | null;
  lead_time_demand: number | null; reorder_point: number | null; eoq: number | null;
  projected_inventory: number | null; projected_shortage: number | null;
  projected_surplus: number | null; raw_requirement: number | null;
  recommended_quantity: number | null; risk_level: "critical" | "high" | "medium" | "low" | "unknown";
  completeness: number; inputs: Record<string, Record<string, unknown>>;
  calculations: Record<string, InventoryCalculation>; constraints: Array<Record<string, unknown>>;
  missing_inputs: string[]; warnings: string[]; explanation: Record<string, unknown>;
  evidence: Record<string, unknown>;
};

export type InventorySummary = {
  series_analyzed: number; risk_counts: Record<InventoryItem["risk_level"], number>;
  insufficient_coverage: number; projected_shortage: number | null;
  projected_surplus: number | null; calculable_recommendations: number;
  manual_review_required: number; input_completeness: number;
};

export type InventoryRunSummary = {
  id: string; dataset_id: string | null; forecast_run_id: string | null;
  scenario_run_id: string | null; source_mode: "official" | "demo"; cutoff: string;
  created_at: string; available_at: string; calculation_version: string;
  status: string; summary: InventorySummary;
};

export type InventoryRun = InventoryRunSummary & {
  portfolio_run_id: string | null; decision_run_id: string | null;
  source_snapshot: Record<string, unknown>; assumptions: Record<string, unknown>;
  missing_inputs: string[]; scope: Record<string, unknown>; coverage: Record<string, unknown>;
  warnings: string[]; provenance: Record<string, unknown>; items: InventoryItem[];
};
