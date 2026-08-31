"use client";

import { Boxes, History, Play, RefreshCw, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { PortfolioDetail } from "@/components/portfolio/portfolio-detail";
import { PortfolioMatrix } from "@/components/portfolio/portfolio-matrix";
import {
  createPortfolio,
  getPortfolioRun,
  listPortfolioForecasts,
  listPortfolioRuns,
  preflightPortfolio,
  regeneratePortfolioDemo,
} from "@/lib/portfolio-api";
import type {
  ForecastRunSummary,
  OperationalDraft,
  PortfolioItem,
  PortfolioPreflight,
  PortfolioRun,
  PortfolioRunSummary,
} from "@/lib/portfolio-types";
import { translateFrequency, ui } from "@/lib/i18n";

function toLocalInput(value: Date) {
  const local = new Date(value);
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  return local.toISOString().slice(0, 16);
}

const emptyDraft = (): OperationalDraft => ({ current_inventory: "", inbound_inventory: "", safety_stock: "", lead_time: "" });

export function Portfolio() {
  const copy = ui.portfolio;
  const [forecasts, setForecasts] = useState<ForecastRunSummary[]>([]);
  const [scopeKey, setScopeKey] = useState("");
  const [cutoff, setCutoff] = useState("");
  const [preflight, setPreflight] = useState<PortfolioPreflight | null>(null);
  const [drafts, setDrafts] = useState<Record<string, OperationalDraft>>({});
  const [runs, setRuns] = useState<PortfolioRunSummary[]>([]);
  const [run, setRun] = useState<PortfolioRun | null>(null);
  const [selected, setSelected] = useState<PortfolioItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scopeWarning, setScopeWarning] = useState<string | null>(null);
  const [historyWarning, setHistoryWarning] = useState<string | null>(null);

  const groups = useMemo(() => {
    const grouped = new Map<string, ForecastRunSummary[]>();
    forecasts.filter((item) => item.status === "completed").forEach((item) => {
      const key = `${item.dataset_id}|${item.frequency}|${item.requested_horizon}`;
      grouped.set(key, [...(grouped.get(key) ?? []), item]);
    });
    return [...grouped.entries()];
  }, [forecasts]);

  const selectedForecastIds = useMemo(() => groups.find(([key]) => key === scopeKey)?.[1].map((item) => item.id) ?? [], [groups, scopeKey]);
  const selectedDataset = groups.find(([key]) => key === scopeKey)?.[1][0]?.dataset_id ?? null;

  useEffect(() => {
    let active = true;
    const forecastTask = listPortfolioForecasts().then((forecastItems) => {
      if (!active) return;
      setForecasts(forecastItems);
      setScopeWarning(null);
      const first = forecastItems.find((item) => item.status === "completed");
      if (first) setScopeKey(`${first.dataset_id}|${first.frequency}|${first.requested_horizon}`);
    }).catch((cause: Error) => {
      if (active) setScopeWarning(cause.message || copy.notices.forecastUnavailable);
    });
    const historyTask = listPortfolioRuns().then((runItems) => {
      if (!active) return;
      setRuns(runItems);
      setHistoryWarning(null);
    }).catch((cause: Error) => {
      if (active) setHistoryWarning(cause.message || copy.notices.historyUnavailable);
    });
    void Promise.allSettled([forecastTask, historyTask]).then(() => {
      if (!active) return;
      setCutoff(toLocalInput(new Date()));
      setLoading(false);
    });
    return () => { active = false; };
  }, [copy.notices.forecastUnavailable, copy.notices.historyUnavailable]);

  useEffect(() => {
    if (!selectedForecastIds.length || !cutoff) return;
    let active = true;
    void preflightPortfolio({ forecastRunIds: selectedForecastIds, datasetId: selectedDataset, cutoff: new Date(cutoff).toISOString() }).then((result) => {
      if (!active) return;
      setPreflight(result);
      setDrafts((current) => Object.fromEntries(result.candidates.map((candidate) => [candidate.forecast_run_id, current[candidate.forecast_run_id] ?? emptyDraft()])));
      setScopeWarning(null);
    }).catch((cause: Error) => active && setScopeWarning(cause.message));
    return () => { active = false; };
  }, [selectedForecastIds, selectedDataset, cutoff]);

  async function analyze() {
    if (!preflight || !cutoff) return;
    setAnalyzing(true); setError(null);
    try {
      const result = await createPortfolio({ forecastRunIds: preflight.candidates.map((item) => item.forecast_run_id), datasetId: preflight.dataset_id, cutoff: new Date(cutoff).toISOString(), operationalDrafts: drafts });
      setRun(result); setSelected(result.items[0] ?? null);
      void listPortfolioRuns().then((items) => { setRuns(items); setHistoryWarning(null); }).catch((cause: Error) => setHistoryWarning(cause.message || copy.notices.historyUnavailable));
    } catch (cause) { setError(cause instanceof Error ? cause.message : copy.error); }
    finally { setAnalyzing(false); }
  }

  async function demo() {
    setAnalyzing(true); setDemoLoading(true); setError(null);
    try {
      const result = await regeneratePortfolioDemo();
      setRun(result); setSelected(result.items[0] ?? null);
      void listPortfolioRuns().then((items) => { setRuns(items); setHistoryWarning(null); }).catch((cause: Error) => setHistoryWarning(cause.message || copy.notices.historyUnavailable));
    }
    catch (cause) { setError(cause instanceof Error ? cause.message : copy.error); }
    finally { setDemoLoading(false); setAnalyzing(false); }
  }

  async function openStored(item: PortfolioRunSummary) {
    setAnalyzing(true); setError(null);
    try { const stored = await getPortfolioRun(item.id); setRun(stored); setSelected(stored.items[0] ?? null); }
    catch (cause) { setError(cause instanceof Error ? cause.message : copy.error); }
    finally { setAnalyzing(false); }
  }

  function updateDraft(runId: string, field: keyof OperationalDraft, value: string) {
    setDrafts((current) => ({ ...current, [runId]: { ...(current[runId] ?? emptyDraft()), [field]: value } }));
  }

  if (loading) return <div className="workspace pf-workspace"><div className="pf-loading"><RefreshCw size={18} />{copy.loading}</div></div>;
  return (
    <div className="workspace pf-workspace">
      <header className="workspace-header pf-header"><div><span className="eyebrow">{copy.header.eyebrow}</span><h1>{copy.header.title}</h1><p>{copy.header.subtitle}</p></div><div className="pf-boundary"><ShieldCheck size={18} /><span>{copy.header.boundary}<strong>{copy.header.noExecution}</strong></span></div></header>
      <section className="pf-panel"><div className="pf-heading"><div><span>{copy.scope.index}</span><h2>{copy.scope.title}</h2></div><small>{preflight?.readiness === "ready" ? copy.scope.ready : copy.scope.partial}</small></div>
        <div className="pf-scope-grid"><label><span>{copy.scope.forecasts}</span><select value={scopeKey} disabled={analyzing || !groups.length} onChange={(event) => { setScopeKey(event.target.value); setPreflight(null); setRun(null); setSelected(null); setScopeWarning(null); }}>{groups.map(([key, items]) => <option key={key} value={key}>{items[0].dataset_id.slice(0, 8)} · {translateFrequency(items[0].frequency)} · {items[0].requested_horizon} periodos · {items.length} runs</option>)}</select></label><label><span>Cutoff</span><input type="datetime-local" value={cutoff} disabled={analyzing} onChange={(event) => { setCutoff(event.target.value); setPreflight(null); setScopeWarning(null); }} /></label></div>
        {scopeWarning && <div className="pf-notice" role="status">{scopeWarning}</div>}
        {preflight && <><div className="pf-source-strip"><div><span>{copy.scope.dataset}</span><strong>{preflight.candidates[0]?.dataset_name ?? "—"}</strong></div><div><span>{copy.scope.series}</span><strong>{preflight.series_compatible}</strong></div><div><span>{copy.scope.frequency}</span><strong>{preflight.frequency ? translateFrequency(preflight.frequency) : "—"}</strong></div><div><span>{copy.scope.horizon}</span><strong>{preflight.horizon ?? "—"}</strong></div><div><span>{copy.scope.inputQuality}</span><strong>{preflight.missing_operational_inputs.length ? copy.scope.partial : copy.scope.ready}</strong></div></div><div className="pf-input-editor"><div className="pf-input-editor-head"><span>{copy.inputs.index}</span><h3>{copy.inputs.title}</h3><p>{copy.inputs.note}</p></div>{preflight.candidates.map((candidate) => <div className="pf-input-row" key={candidate.forecast_run_id}><div><strong>{candidate.product ?? copy.allProducts} · {candidate.location ?? copy.allLocations}</strong><small>{candidate.forecast_run_id.slice(0, 8)} · {candidate.champion}</small></div>{(["current_inventory", "inbound_inventory", "safety_stock", "lead_time"] as const).map((field) => <label key={field}><span>{copy.inputLabels[field]}</span><input type="number" min="0" step="any" placeholder={copy.missing} value={drafts[candidate.forecast_run_id]?.[field] ?? ""} onChange={(event) => updateDraft(candidate.forecast_run_id, field, event.target.value)} /></label>)}</div>)}</div></>}
        {error && <div className="ds-error-message">{error}</div>}<div className="pf-actions"><button type="button" className="pf-secondary" disabled={analyzing} onClick={() => void demo()}>{demoLoading ? <RefreshCw size={16} /> : <Boxes size={16} />}{demoLoading ? copy.demo.loading : copy.demo.action}</button><button type="button" className="pf-primary" disabled={analyzing || !preflight} onClick={() => void analyze()}>{analyzing && !demoLoading ? <RefreshCw size={16} /> : <Play size={16} />}{analyzing && !demoLoading ? copy.scope.analyzing : copy.scope.analyze}</button></div>
      </section>
      {run && <><section className="pf-kpis"><article><span>{copy.summary.series}</span><strong>{run.summary.series_evaluated}</strong></article><article><span>{copy.summary.high}</span><strong>{run.summary.risk_counts.critical + run.summary.risk_counts.high}</strong></article><article><span>{copy.summary.incomplete}</span><strong>{run.summary.completeness_counts.partial_data + run.summary.completeness_counts.insufficient_data}</strong></article><article><span>{copy.summary.forecast}</span><strong>{run.summary.forecast_total_aggregate == null ? copy.notCalculable : new Intl.NumberFormat("es-PE", { maximumFractionDigits: 1 }).format(run.summary.forecast_total_aggregate)}</strong></article><article><span>{copy.summary.coverage}</span><strong>{run.summary.coverage_evaluable_series}/{run.summary.series_evaluated}</strong></article></section><PortfolioMatrix items={run.items} selectedId={selected?.id ?? null} onSelect={setSelected} /><PortfolioDetail item={selected} run={run} /></>}
      <section className="pf-panel"><div className="pf-heading"><div><span>{copy.history.index}</span><h2>{copy.history.title}</h2></div><History size={17} /></div>{historyWarning && <div className="pf-notice" role="status">{historyWarning}</div>}{!runs.length ? <p className="pf-muted">{copy.history.empty}</p> : <div className="pf-history">{runs.map((item) => <button type="button" key={item.id} disabled={analyzing} onClick={() => void openStored(item)}><span><strong>{new Date(item.created_at).toLocaleDateString("es-PE")} · {item.number_of_series} series</strong><small>{item.source_mode === "demo" ? copy.demo.badge : item.dataset_id}</small></span><b>{item.summary.risk_counts.critical + item.summary.risk_counts.high} {copy.history.attention}</b></button>)}</div>}</section>
    </div>
  );
}
