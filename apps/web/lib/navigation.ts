import {
  Boxes,
  ChartLine,
  CircleGauge,
  FileText,
  FlaskConical,
  LayoutGrid,
  Radar,
  Route,
  ScanSearch,
  Sparkles,
  Table2,
  type LucideIcon,
} from "lucide-react";

import { ui } from "@/lib/i18n";

export type NavigationSection = {
  slug: string;
  label: string;
  description: string;
  icon: LucideIcon;
};

export const sections: NavigationSection[] = [
  { slug: "command-center", ...ui.navigation.sections.commandCenter, icon: LayoutGrid },
  { slug: "data-studio", ...ui.navigation.sections.dataStudio, icon: Table2 },
  { slug: "demand-explorer", ...ui.navigation.sections.demandExplorer, icon: ChartLine },
  { slug: "forecast-lab", ...ui.navigation.sections.forecastLab, icon: FlaskConical },
  { slug: "context-radar", ...ui.navigation.sections.contextRadar, icon: Radar },
  { slug: "scenario-lab", ...ui.navigation.sections.scenarioLab, icon: Sparkles },
  { slug: "decision-center", ...ui.navigation.sections.decisionCenter, icon: CircleGauge },
  { slug: "scor-diagnostic", ...ui.navigation.sections.scorDiagnostic, icon: Route },
  { slug: "portfolio", ...ui.navigation.sections.portfolio, icon: Boxes },
  { slug: "model-explain", ...ui.navigation.sections.modelExplain, icon: ScanSearch },
  { slug: "reports", ...ui.navigation.sections.reports, icon: FileText },
];
