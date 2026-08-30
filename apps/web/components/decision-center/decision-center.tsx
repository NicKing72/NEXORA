"use client";

import { BrainCircuit, History, Play, RefreshCw, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { DecisionComparison } from "@/components/decision-center/decision-comparison";
import { DecisionDetail } from "@/components/decision-center/decision-detail";
import { DecisionList } from "@/components/decision-center/decision-list";
import {
  createDecisionRun,
  getDecisionPreflight,
  getDecisionRun,
  listDecisionForecasts,
  listDecisionRuns,
  updateDecisionStatus,
} from "@/lib/decision-api";
import type {
  DecisionPreflight,
  DecisionRecommendation,
  DecisionRun,
  DecisionRunSummary,
  DecisionStatus,
  ForecastRunSummary,
} from "@/lib/decision-types";
import { translateFrequency, ui } from "@/lib/i18n";

function toLocalInput(value: Date) {
  const local = new Date(value);
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  return local.toISOString().slice(0, 16);
}

function percent(value: number | null | undefined) {
  if (value == null) return "—";
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
}

export function DecisionCenter() {
  const copy = ui.decisionCenter;
  const [forecasts, setForecasts] = useState<ForecastRunSummary[]>([]);
  const [forecastRunId, setForecastRunId] = useState("");
  const [scenarioRunId, setScenarioRunId] = useState("");
  const [cutoff, setCutoff] = useState("");
  const [preflight, setPreflight] = useState<DecisionPreflight | null>(null);
  const [runs, setRuns] = useState<DecisionRunSummary[]>([]);
  const [run, setRun] = useState<DecisionRun | null>(null);
  const [selected, setSelected] = useState<DecisionRecommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryRef = useRef<URLSearchParams | null>(null);

  useEffect(() => {
    queryRef.current = new URLSearchParams(window.location.search);
    let active = true;
    const localCutoff = toLocalInput(new Date());
    Promise.all([listDecisionForecasts(), listDecisionRuns()])
      .then(([forecastItems, runItems]) => {
        if (!active) return;
        const completed = forecastItems.filter((item) => item.status === "completed");
        const requestedRun = queryRef.current?.get("forecast_run_id");
        const requestedDataset = queryRef.current?.get("dataset_id");
        const preferred = completed.find((item) => item.id === requestedRun)
          ?? completed.find((item) => item.dataset_id === requestedDataset)
          ?? completed[0];
        setForecasts(completed);
        setRuns(runItems);
        setCutoff(localCutoff);
        setForecastRunId(preferred?.id ?? "");
      })
      .catch((cause: Error) => active && setError(cause.message))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!forecastRunId || !cutoff) return;
    let active = true;
    const decisionCutoff = new Date(cutoff).toISOString();
    void getDecisionPreflight({ forecastRunId, scenarioRunId, decisionCutoff })
      .then((result) => {
        if (!active) return;
        setPreflight(result);
        const requestedScenario = queryRef.current?.get("scenario_run_id");
        if (!scenarioRunId && requestedScenario && result.scenarios.some((item) => item.id === requestedScenario)) {
          setScenarioRunId(requestedScenario);
        }
        queryRef.current = null;
      })
      .catch((cause: Error) => active && setError(cause.message));
    return () => { active = false; };
  }, [forecastRunId, scenarioRunId, cutoff]);

  const activeForecast = useMemo(
    () => forecasts.find((item) => item.id === forecastRunId) ?? null,
    [forecasts, forecastRunId],
  );
  const openCount = run?.recommendations.filter((item) => ["open", "acknowledged", "under_review"].includes(item.status)).length ?? 0;

  async function analyze() {
    if (!forecastRunId || !cutoff) return;
    setAnalyzing(true);
    setError(null);
    try {
      const result = await createDecisionRun({
        forecastRunId,
        scenarioRunId,
        decisionCutoff: new Date(cutoff).toISOString(),
      });
      setRun(result);
      setSelected(result.recommendations[0] ?? null);
      setRuns(await listDecisionRuns());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy.error);
    } finally {
      setAnalyzing(false);
    }
  }

  async function openStored(item: DecisionRunSummary) {
    setAnalyzing(true);
    setError(null);
    try {
      const stored = await getDecisionRun(item.id);
      setForecastRunId(stored.forecast_run_id);
      setScenarioRunId(stored.scenario_run_id ?? "");
      setCutoff(toLocalInput(new Date(stored.decision_cutoff)));
      setRun(stored);
      setSelected(stored.recommendations[0] ?? null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy.error);
    } finally {
      setAnalyzing(false);
    }
  }

  async function updateStatus(status: DecisionStatus) {
    if (!selected || !run) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateDecisionStatus(selected.id, status);
      const recommendations = run.recommendations.map((item) => item.id === updated.id ? updated : item);
      setRun({ ...run, recommendations });
      setSelected(updated);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy.error);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="workspace dc-workspace"><div className="dc-loading"><RefreshCw size={18} />Preparando evidencia para decisiones…</div></div>;
  if (!forecasts.length) return <div className="workspace dc-workspace"><header className="workspace-header"><div><span className="eyebrow">{copy.header.eyebrow}</span><h1>{copy.header.title}</h1><p>{copy.header.subtitle}</p></div></header><section className="dc-empty"><BrainCircuit size={30} /><h2>{copy.empty.title}</h2><p>{copy.empty.description}</p><Link href="/forecast-lab" className="dx-primary-action">{copy.empty.action}</Link></section></div>;

  return <div className="workspace dc-workspace"><header className="workspace-header dc-header"><div><span className="eyebrow">{copy.header.eyebrow}</span><h1>{copy.header.title}</h1><p>{copy.header.subtitle}</p></div><div className="dc-boundary"><ShieldCheck size={18} /><span>{copy.header.boundary}<strong>{copy.header.noExecution}</strong></span></div></header><section className="dc-panel"><div className="dc-heading"><div><span>{copy.setup.index}</span><h2>{copy.setup.title}</h2></div><small>{preflight?.selection.dataset_name ?? "—"}</small></div><div className="dc-setup-grid"><label><span>{copy.setup.forecast}</span><select value={forecastRunId} disabled={analyzing} onChange={(event) => { setForecastRunId(event.target.value); setScenarioRunId(""); setRun(null); setSelected(null); }}>{forecasts.map((item) => <option key={item.id} value={item.id}>{item.data_cutoff} · {translateFrequency(item.frequency)} · {item.champion_model}</option>)}</select></label><label><span>{copy.setup.scenario}</span><select value={scenarioRunId} disabled={analyzing || !preflight} onChange={(event) => { setScenarioRunId(event.target.value); setRun(null); setSelected(null); }}><option value="">{copy.setup.noScenario}</option>{preflight?.scenarios.map((item) => <option key={item.id} value={item.id}>{item.name} · {percent(item.relative_delta)}</option>)}</select></label><label><span>{copy.setup.cutoff}</span><input type="datetime-local" value={cutoff} disabled={analyzing} onChange={(event) => setCutoff(event.target.value)} /></label></div>{preflight && <div className="dc-source-strip"><div><span>{copy.setup.champion}</span><strong>{preflight.champion.model_name}</strong></div><div><span>{copy.setup.trajectory}</span><strong>{percent(preflight.forecast_summary.trajectory_delta)}</strong></div><div><span>{copy.setup.context}</span><strong>{preflight.relevant_context.length}</strong></div><div><span>{copy.setup.impacts}</span><strong>{preflight.usable_impacts.length}</strong></div><div><span>{copy.setup.missing}</span><strong>{preflight.missing_operational_inputs.length}</strong></div></div>}{scenarioRunId && <p className="dc-scenario-boundary">{copy.setup.scenarioBoundary}</p>}{error && <div className="ds-error-message">{error}</div>}<div className="dc-run"><button type="button" disabled={analyzing || !preflight} onClick={() => void analyze()}>{analyzing ? <RefreshCw size={16} /> : <Play size={16} />}{analyzing ? copy.setup.analyzing : copy.setup.analyze}</button><small>Forecast: {activeForecast?.id} · corte auditable {cutoff}</small></div></section>{run && <><section className="dc-kpis"><article><span>{copy.kpis.open}</span><strong>{openCount}</strong></article><article><span>{copy.kpis.high}</span><strong>{run.summary.high_priority_count}</strong></article><article><span>{copy.kpis.review}</span><strong>{run.summary.requires_review_count}</strong></article><article><span>{copy.kpis.scenarios}</span><strong>{run.summary.scenario_considered ? 1 : 0}</strong></article></section><DecisionList recommendations={run.recommendations} selectedId={selected?.id ?? null} onSelect={setSelected} /><DecisionDetail recommendation={selected} saving={saving} onStatus={(status) => void updateStatus(status)} /><DecisionComparison run={run} /></>}<section className="dc-panel"><div className="dc-heading"><div><span>{copy.history.index}</span><h2>{copy.history.title}</h2></div><History size={17} /></div>{!runs.length ? <p className="dc-muted">{copy.history.empty}</p> : <div className="dc-history">{runs.map((item) => <button type="button" key={item.id} disabled={analyzing} onClick={() => void openStored(item)}><span><strong>{item.created_at.slice(0, 10)} · {item.recommendation_count} recomendaciones</strong><small>{item.forecast_run_id}{item.scenario_run_id ? " · con escenario" : " · baseline oficial"}</small></span><b>{item.high_priority_count} alta/crítica</b></button>)}</div>}</section></div>;
}
