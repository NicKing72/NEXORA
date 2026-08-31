import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { CommandCenter } from "@/components/command-center";
import { ContextRadar } from "@/components/context-radar/context-radar";
import { DataStudio } from "@/components/data-studio/data-studio";
import { DecisionCenter } from "@/components/decision-center/decision-center";
import { DemandExplorer } from "@/components/demand-explorer/demand-explorer";
import { ForecastLab } from "@/components/forecast-lab/forecast-lab";
import { ExplanationCenter } from "@/components/model-explanation/explanation-center";
import { PlaceholderView } from "@/components/placeholder-view";
import { Portfolio } from "@/components/portfolio/portfolio";
import { ReportCenter } from "@/components/reports/report-center";
import { ScenarioLab } from "@/components/scenario-lab/scenario-lab";
import { ScorDiagnostic } from "@/components/scor-diagnostic/scor-diagnostic";
import { sections } from "@/lib/navigation";

type SectionPageProps = {
  params: Promise<{ section: string }>;
};

export function generateStaticParams() {
  return sections.map(({ slug }) => ({ section: slug }));
}

export async function generateMetadata({ params }: SectionPageProps): Promise<Metadata> {
  const { section: slug } = await params;
  const section = sections.find((item) => item.slug === slug);

  return section ? { title: section.label } : {};
}

export default async function SectionPage({ params }: SectionPageProps) {
  const { section: slug } = await params;
  const section = sections.find((item) => item.slug === slug);

  if (!section) {
    notFound();
  }

  if (section.slug === "command-center") {
    return <CommandCenter />;
  }

  if (section.slug === "data-studio") {
    return <DataStudio />;
  }

  if (section.slug === "demand-explorer") {
    return <DemandExplorer />;
  }

  if (section.slug === "forecast-lab") {
    return <ForecastLab />;
  }

  if (section.slug === "context-radar") {
    return <ContextRadar />;
  }

  if (section.slug === "scenario-lab") {
    return <ScenarioLab />;
  }

  if (section.slug === "decision-center") {
    return <DecisionCenter />;
  }

  if (section.slug === "scor-diagnostic") {
    return <ScorDiagnostic />;
  }

  if (section.slug === "portfolio") {
    return <Portfolio />;
  }

  if (section.slug === "model-explain") {
    return <ExplanationCenter />;
  }

  if (section.slug === "reports") {
    return <ReportCenter />;
  }

  return <PlaceholderView section={section} />;
}
