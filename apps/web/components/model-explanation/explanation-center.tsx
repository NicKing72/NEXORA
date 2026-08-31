"use client";

import { Database, RefreshCw, ScanSearch } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { ChampionExplanation } from "@/components/model-explanation/champion-explanation";
import { ExplanationHeader } from "@/components/model-explanation/explanation-header";
import { ExplanationHistory } from "@/components/model-explanation/explanation-history";
import { ForecastExplanation } from "@/components/model-explanation/forecast-explanation";
import { LimitationPanel } from "@/components/model-explanation/limitation-panel";
import { ModelComparison } from "@/components/model-explanation/model-comparison";
import { ExplanationModelDetail } from "@/components/model-explanation/model-detail";
import { ProvenancePanel } from "@/components/model-explanation/provenance-panel";
import { ValidationHistory } from "@/components/model-explanation/validation-history";
import {
  createExplanation,
  getExplanation,
  getExplanationForecasts,
  getExplanationPreflight,
  getExplanations,
} from "@/lib/explanation-api";
import type {
  ExplanationModel,
  ExplanationPreflight,
  ExplanationRequest,
  ExplanationRun,
  ExplanationRunSummary,
  ForecastRunSummary,
} from "@/lib/explanation-types";
import { ui } from "@/lib/i18n";

const SOURCE_KEYS = ["scenario_run_id", "scor_assessment_id", "portfolio_run_id", "decision_run_id"] as const;

function toLocalDateTimeInput(date: Date) {
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return localDate.toISOString().slice(0, 16);
}

export function ExplanationCenter() {
  const copy = ui.modelExplanation;
  const [forecasts, setForecasts] = useState<ForecastRunSummary[]>([]);
  const [history, setHistory] = useState<ExplanationRunSummary[]>([]);
  const [forecastId, setForecastId] = useState("");
  const [cutoff, setCutoff] = useState("");
  const [sourceIds, setSourceIds] = useState<Record<string, string>>({});
  const [preflight, setPreflight] = useState<ExplanationPreflight | null>(null);
  const [run, setRun] = useState<ExplanationRun | null>(null);
  const [selectedModel, setSelectedModel] = useState<ExplanationModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryRef = useRef<URLSearchParams | null>(null);

  useEffect(() => {
    queryRef.current = new URLSearchParams(window.location.search);
    const controller = new AbortController();
    Promise.all([getExplanationForecasts(controller.signal), getExplanations(controller.signal)])
      .then(([forecastItems, explanationItems]) => {
        setCutoff(toLocalDateTimeInput(new Date()));
        const completed = forecastItems.filter((item) => item.status === "completed" && item.champion_model);
        const requestedForecast = queryRef.current?.get("forecast_run_id");
        const selected = completed.find((item) => item.id === requestedForecast) ?? completed[0] ?? null;
        const nextSources: Record<string, string> = {};
        SOURCE_KEYS.forEach((key) => {
          const value = queryRef.current?.get(key);
          if (value) nextSources[key] = value;
        });
        setForecasts(completed);
        setHistory(explanationItems);
        setForecastId(selected?.id ?? "");
        setSourceIds(nextSources);
        const requestedExplanation = queryRef.current?.get("explanation_id");
        if (requestedExplanation && explanationItems.some((item) => item.id === requestedExplanation)) {
          return getExplanation(requestedExplanation, controller.signal).then(selectRun);
        }
      })
      .catch((cause: Error) => { if (cause.name !== "AbortError") setError(copy.errors.load); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [copy.errors.load]);

  const request = useMemo<ExplanationRequest | null>(() => {
    if (!forecastId) return null;
    return {
      forecast_run_id: forecastId,
      cutoff: cutoff ? new Date(cutoff).toISOString() : undefined,
      scenario_run_id: sourceIds.scenario_run_id ?? null,
      scor_assessment_id: sourceIds.scor_assessment_id ?? null,
      portfolio_run_id: sourceIds.portfolio_run_id ?? null,
      decision_run_id: sourceIds.decision_run_id ?? null,
    };
  }, [cutoff, forecastId, sourceIds]);

  useEffect(() => {
    if (!request || run?.forecast_run_id === request.forecast_run_id) return;
    const controller = new AbortController();
    void getExplanationPreflight(request, controller.signal)
      .then((result) => { setPreflight(result); setError(null); })
      .catch((cause: Error) => { if (cause.name !== "AbortError") setError(copy.errors.preflight); });
    return () => controller.abort();
  }, [copy.errors.preflight, request, run?.forecast_run_id]);

  function selectRun(next: ExplanationRun) {
    setRun(next);
    setForecastId(next.forecast_run_id);
    setSelectedModel(next.source_snapshot.comparison.find((item) => item.is_champion) ?? next.source_snapshot.comparison[0] ?? null);
    setPreflight(null);
  }

  function updateUrl(explanationId: string, nextForecastId = forecastId) {
    const parameters = new URLSearchParams({ forecast_run_id: nextForecastId, explanation_id: explanationId });
    SOURCE_KEYS.forEach((key) => { if (sourceIds[key]) parameters.set(key, sourceIds[key]); });
    window.history.replaceState(null, "", `/model-explain?${parameters.toString()}`);
  }

  function changeForecast(nextId: string) {
    setForecastId(nextId);
    setRun(null);
    setSelectedModel(null);
    setPreflight(null);
    const parameters = new URLSearchParams({ forecast_run_id: nextId });
    window.history.replaceState(null, "", `/model-explain?${parameters.toString()}`);
  }

  async function generate() {
    if (!request) return;
    setGenerating(true);
    setError(null);
    try {
      const result = await createExplanation(request);
      selectRun(result);
      setHistory((current) => [result, ...current.filter((item) => item.id !== result.id)]);
      updateUrl(result.id, result.forecast_run_id);
    } catch {
      setError(copy.errors.create);
    } finally {
      setGenerating(false);
    }
  }

  async function recover(id: string) {
    setError(null);
    try {
      const result = await getExplanation(id);
      selectRun(result);
      updateUrl(result.id, result.forecast_run_id);
    } catch {
      setError(copy.errors.recovery);
    }
  }

  const selectedForecast = forecasts.find((item) => item.id === forecastId) ?? null;
  const scope = run?.source_snapshot.scope ?? preflight?.scope ?? null;
  return (
    <div className="workspace mx-workspace">
      <ExplanationHeader />
      <section className="mx-panel mx-scope">
        <div className="mx-section-heading"><div><span>{copy.scope.index}</span><h2>{copy.scope.title}</h2></div>{selectedForecast && <small><Database size={14} />{selectedForecast.dataset_id}</small>}</div>
        {loading ? <p className="mx-loading"><RefreshCw size={16} />{copy.scope.loading}</p> : forecasts.length === 0 ? <p>{copy.scope.noForecasts}</p> : <>
          <div className="mx-scope-controls"><label><span>{copy.scope.forecast}</span><select value={forecastId} disabled={generating} onChange={(event) => changeForecast(event.target.value)}>{forecasts.map((item) => <option key={item.id} value={item.id}>{item.data_cutoff} · {item.frequency} · {ui.forecastLab.modelNames[item.champion_model as keyof typeof ui.forecastLab.modelNames] ?? item.champion_model} · {item.id.slice(0, 8)}</option>)}</select></label><label><span>{copy.scope.cutoff}</span><input type="datetime-local" value={cutoff} disabled={generating} onChange={(event) => { setCutoff(event.target.value); setRun(null); }} /></label><button type="button" disabled={!preflight || generating} onClick={() => void generate()}>{generating ? <RefreshCw size={17} /> : <ScanSearch size={17} />}{generating ? copy.scope.generating : copy.scope.action}</button></div>
          {scope && <div className="mx-scope-grid"><div><small>{copy.scope.dataset}</small><strong>{scope.dataset_name}</strong></div><div><small>{copy.scope.product}</small><strong>{scope.product ?? ui.demandExplorer.selector.allProducts}</strong></div><div><small>{copy.scope.location}</small><strong>{scope.location ?? ui.demandExplorer.selector.allLocations}</strong></div><div><small>{copy.scope.frequency}</small><strong>{scope.frequency}</strong></div><div><small>{copy.scope.horizon}</small><strong>{scope.horizon} {copy.scope.periods}</strong></div><div><small>{copy.scope.champion}</small><strong>{selectedForecast?.champion_model ?? "—"}</strong></div></div>}
        </>}
        {error && <div className="ds-error-message">{error}</div>}
      </section>
      {run && <>
        <ChampionExplanation run={run} />
        <ModelComparison models={run.source_snapshot.comparison} selectedId={selectedModel?.id ?? null} onSelect={setSelectedModel} />
        <ExplanationModelDetail model={selectedModel} />
        <ValidationHistory run={run} />
        <ForecastExplanation run={run} />
        <div className="mx-audit-grid"><ProvenancePanel run={run} /><LimitationPanel run={run} /></div>
      </>}
      <ExplanationHistory items={history} selectedId={run?.id ?? null} onSelect={(id) => void recover(id)} />
    </div>
  );
}
