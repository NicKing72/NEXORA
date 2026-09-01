"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { ReportBuilder } from "@/components/reports/report-builder";
import { ReportDashboard } from "@/components/reports/report-dashboard";
import { ReportHeader } from "@/components/reports/report-header";
import { ReportHistory } from "@/components/reports/report-history";
import { ReportPreflightPanel } from "@/components/reports/report-preflight";
import { ui } from "@/lib/i18n";
import {
  createReport,
  getReportDefinitions,
  getReportPreflight,
  getReportRun,
  getReportSourceOptions,
  listReportRuns,
  regenerateReportDemo,
} from "@/lib/report-api";
import type {
  ReportPreflight,
  ReportRequest,
  ReportRun,
  ReportRunSummary,
  SourceSummary,
} from "@/lib/report-types";

const SOURCE_FIELDS = {
  forecast_run_id: "forecasts",
  scenario_run_id: "scenarios",
  scor_assessment_id: "scor",
  portfolio_run_id: "portfolios",
  decision_run_id: "decisions",
  explanation_run_id: "explanations",
} as const;

function localInput(date: Date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function initialRequest(): ReportRequest {
  return {
    report_type: "integrated",
    title: "Reporte ejecutivo integrado NEXORA",
    report_cutoff: "",
    forecast_run_id: null,
    scenario_run_id: null,
    scor_assessment_id: null,
    portfolio_run_id: null,
    decision_run_id: null,
    explanation_run_id: null,
  };
}

function compatible(item: SourceSummary, forecastId: string | null, field: string) {
  if (!forecastId || field === "forecasts") return true;
  if (field === "portfolios") return item.forecast_run_ids?.includes(forecastId) ?? false;
  return item.forecast_run_id == null || item.forecast_run_id === forecastId;
}

export function ReportCenter() {
  const [request, setRequest] = useState<ReportRequest>(initialRequest);
  const [options, setOptions] = useState<Record<string, SourceSummary[]>>({});
  const [history, setHistory] = useState<ReportRunSummary[]>([]);
  const [preflight, setPreflight] = useState<ReportPreflight | null>(null);
  const [run, setRun] = useState<ReportRun | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [validating, setValidating] = useState<boolean>(false);
  const [generating, setGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const queryRef = useRef<URLSearchParams | null>(null);

  useEffect(() => {
    queryRef.current = new URLSearchParams(window.location.search);
    Promise.all([getReportDefinitions(), getReportSourceOptions(), listReportRuns()])
      .then(async ([, sourceOptions, reportHistory]) => {
        const next = initialRequest();
        next.report_cutoff = localInput(new Date());
        const requestedForecast = queryRef.current?.get("forecast_run_id") ?? null;
        if (requestedForecast && sourceOptions.forecasts.some((item) => item.id === requestedForecast)) {
          next.forecast_run_id = requestedForecast;
        } else if (requestedForecast) {
          setError(ui.reports.errors.invalidHandoff);
        }
        Object.entries(SOURCE_FIELDS).forEach(([field, group]) => {
          if (field === "forecast_run_id") return;
          const requested = queryRef.current?.get(field);
          if (!requested) return;
          const exact = sourceOptions[group].find((item) => item.id === requested);
          if (exact && compatible(exact, next.forecast_run_id, group)) {
            next[field as keyof ReportRequest] = requested as never;
          } else {
            setError(ui.reports.errors.invalidHandoff);
          }
        });
        setOptions(sourceOptions);
        setHistory(reportHistory);
        setRequest(next);
        const requestedReport = queryRef.current?.get("report_run_id");
        if (requestedReport) {
          const recovered = await getReportRun(requestedReport);
          setRun(recovered);
        }
      })
      .catch(() => setError(ui.reports.errors.load))
      .finally(() => setLoading(false));
  }, []);

  const compatibleOptions = useMemo(() => Object.fromEntries(
    Object.entries(options).map(([group, items]) => [
      group,
      items.filter((item) => compatible(item, request.forecast_run_id, group)),
    ]),
  ), [options, request.forecast_run_id]);

  const apiRequest = useMemo(() => ({
    ...request,
    report_cutoff: request.report_cutoff ? new Date(request.report_cutoff).toISOString() : "",
  }), [request]);

  function update(key: keyof ReportRequest, value: string | null) {
    setRequest((current) => {
      const next = { ...current, [key]: value };
      if (key === "forecast_run_id") {
        next.scenario_run_id = null;
        next.scor_assessment_id = null;
        next.portfolio_run_id = null;
        next.decision_run_id = null;
        next.explanation_run_id = null;
      }
      return next;
    });
    setPreflight(null);
    setRun(null);
    setError(null);
    window.history.replaceState(null, "", "/reports");
  }

  async function validate() {
    setValidating(true);
    setError(null);
    try {
      setPreflight(await getReportPreflight(apiRequest));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : ui.reports.errors.preflight);
      setPreflight(null);
    } finally {
      setValidating(false);
    }
  }

  function selectRun(next: ReportRun) {
    setRun(next);
    setHistory((current) => [next, ...current.filter((item) => item.id !== next.id)]);
    window.history.replaceState(null, "", `/reports?report_run_id=${next.id}`);
  }

  async function generate() {
    setGenerating(true);
    setError(null);
    try {
      selectRun(await createReport(apiRequest));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : ui.reports.errors.create);
    } finally {
      setGenerating(false);
    }
  }

  async function demo() {
    setGenerating(true);
    setError(null);
    try {
      selectRun(await regenerateReportDemo());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : ui.reports.errors.create);
    } finally {
      setGenerating(false);
    }
  }

  async function recover(id: string) {
    setError(null);
    try {
      selectRun(await getReportRun(id));
    } catch {
      setError(ui.reports.errors.recovery);
    }
  }

  return (
    <div className="workspace rp-workspace">
      <ReportHeader />
      <ReportBuilder request={request} options={compatibleOptions} loading={loading} validating={validating} generating={generating} canGenerate={Boolean(preflight?.ready)} onChange={update} onValidate={() => void validate()} onGenerate={() => void generate()} onDemo={() => void demo()} />
      {error && <div className="ds-error-message" role="alert">{error}</div>}
      {preflight && <ReportPreflightPanel preflight={preflight} />}
      {run && <ReportDashboard run={run} />}
      <ReportHistory items={history} selectedId={run?.id ?? null} onSelect={(id) => void recover(id)} />
    </div>
  );
}
