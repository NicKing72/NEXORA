import type { ReportRequest } from "./report-types.ts";

const IDS = [
  "forecast_run_id",
  "scenario_run_id",
  "scor_assessment_id",
  "portfolio_run_id",
  "decision_run_id",
  "explanation_run_id",
] as const;

export function buildReportsHref(ids: Partial<Record<(typeof IDS)[number], string | null>>) {
  const parameters = new URLSearchParams();
  IDS.forEach((key) => { if (ids[key]) parameters.set(key, ids[key]); });
  return parameters.size ? `/reports?${parameters.toString()}` : "/reports";
}

export function readReportHandoff(search: string): Partial<ReportRequest> {
  const parameters = new URLSearchParams(search);
  return Object.fromEntries(IDS.map((key) => [key, parameters.get(key)])) as Partial<ReportRequest>;
}
