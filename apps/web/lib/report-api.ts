import { apiRequest } from "@/lib/api-client";
import type {
  ReportDefinitions,
  ReportPreflight,
  ReportRequest,
  ReportRun,
  ReportRunSummary,
  SourceSummary,
} from "@/lib/report-types";

const API_ORIGIN = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const getReportDefinitions = (): Promise<ReportDefinitions> =>
  apiRequest("/api/v1/reports/definitions");
export const getReportPreflight = (request: ReportRequest): Promise<ReportPreflight> =>
  apiRequest("/api/v1/reports/preflight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
export const createReport = (request: ReportRequest): Promise<ReportRun> =>
  apiRequest("/api/v1/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
export const regenerateReportDemo = (): Promise<ReportRun> =>
  apiRequest("/api/v1/reports/demo/regenerate", { method: "POST" });
export const listReportRuns = (): Promise<ReportRunSummary[]> => apiRequest("/api/v1/reports");
export const getReportRun = (id: string): Promise<ReportRun> => apiRequest(`/api/v1/reports/${id}`);

export async function getReportSourceOptions(): Promise<Record<string, SourceSummary[]>> {
  const [forecasts, scenarios, scor, portfolios, decisions, explanations] = await Promise.all([
    apiRequest<SourceSummary[]>("/api/v1/forecast-runs"),
    apiRequest<SourceSummary[]>("/api/v1/scenarios"),
    apiRequest<SourceSummary[]>("/api/v1/scor/assessments"),
    apiRequest<SourceSummary[]>("/api/v1/portfolio"),
    apiRequest<SourceSummary[]>("/api/v1/decisions"),
    apiRequest<SourceSummary[]>("/api/v1/explanations"),
  ]);
  return { forecasts, scenarios, scor, portfolios, decisions, explanations };
}

export function reportExportUrl(id: string, format: "html" | "json" | "csv") {
  return `${API_ORIGIN}/api/v1/reports/${id}/export?format=${format}`;
}
