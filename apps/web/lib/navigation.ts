import {
  Boxes,
  ChartLine,
  CircleGauge,
  FileText,
  FlaskConical,
  LayoutGrid,
  Radar,
  ScanSearch,
  Sparkles,
  Table2,
  type LucideIcon,
} from "lucide-react";

export type NavigationSection = {
  slug: string;
  label: string;
  description: string;
  icon: LucideIcon;
};

export const sections: NavigationSection[] = [
  { slug: "command-center", label: "Command Center", description: "A unified operational view of demand health and priorities.", icon: LayoutGrid },
  { slug: "data-studio", label: "Data Studio", description: "Prepare, validate, and govern demand-ready datasets.", icon: Table2 },
  { slug: "demand-explorer", label: "Demand Explorer", description: "Explore demand patterns across products, locations, and time.", icon: ChartLine },
  { slug: "forecast-lab", label: "Forecast Lab", description: "Configure, compare, and evaluate future forecast cycles.", icon: FlaskConical },
  { slug: "context-radar", label: "Context Radar", description: "Understand the external signals shaping demand.", icon: Radar },
  { slug: "scenario-lab", label: "Scenario Lab", description: "Test assumptions and compare operational possibilities.", icon: Sparkles },
  { slug: "decision-center", label: "Decision Center", description: "Turn demand evidence into focused operational actions.", icon: CircleGauge },
  { slug: "portfolio", label: "Portfolio", description: "Monitor products and segments through one structured portfolio.", icon: Boxes },
  { slug: "model-explain", label: "Model Explain", description: "Inspect the future reasoning behind forecast outcomes.", icon: ScanSearch },
  { slug: "reports", label: "Reports", description: "Create clear, repeatable views for stakeholders.", icon: FileText },
];
