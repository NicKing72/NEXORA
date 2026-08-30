"use client";

import { BrainCircuit, Database, FlaskConical, Radar, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { BacktestingView } from "@/components/forecast-lab/backtesting-view";
import { ChampionCard } from "@/components/forecast-lab/champion-card";
import { ForecastChart } from "@/components/forecast-lab/forecast-chart";
import { ForecastSelector } from "@/components/forecast-lab/forecast-selector";
import { Leaderboard } from "@/components/forecast-lab/leaderboard";
import { ModelDetail } from "@/components/forecast-lab/model-detail";
import { PreflightPanel } from "@/components/forecast-lab/preflight-panel";
import { getRelevantSignalsForSeries } from "@/lib/context-api";
import { createForecastRun, getForecastPreflight } from "@/lib/forecast-api";
import type { ForecastModelResult, ForecastPreflight, ForecastRequest, ForecastRun } from "@/lib/forecast-types";
import { getReadyDatasets, getSeriesDimensions } from "@/lib/series-api";
import { ui } from "@/lib/i18n";
import { formatSeriesDate } from "@/lib/series-formatters";
import type { ReadyDatasetSummary, SeriesDimensions } from "@/lib/series-types";

const INITIAL_REQUEST: ForecastRequest = { dataset_id: "", product: null, location: null, category: null, frequency: "auto", horizon: 30 };

export function ForecastLab() {
  const [datasets, setDatasets] = useState<ReadyDatasetSummary[]>([]);
  const [dimensions, setDimensions] = useState<SeriesDimensions | null>(null);
  const [request, setRequest] = useState<ForecastRequest>(INITIAL_REQUEST);
  const [preflight, setPreflight] = useState<ForecastPreflight | null>(null);
  const [run, setRun] = useState<ForecastRun | null>(null);
  const [selectedModel, setSelectedModel] = useState<ForecastModelResult | null>(null);
  const [contextSignalCount, setContextSignalCount] = useState<number | null>(null);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [loadingPreflight, setLoadingPreflight] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryRef = useRef<URLSearchParams | null>(null);

  useEffect(() => {
    queryRef.current = new URLSearchParams(window.location.search);
    const controller = new AbortController();
    void getReadyDatasets(controller.signal).then((items) => {
      const preferred = queryRef.current?.get("dataset_id");
      const datasetId = items.some((item) => item.id === preferred) ? preferred! : items[0]?.id ?? "";
      setDatasets(items);
      setRequest((current) => ({ ...current, dataset_id: datasetId }));
    }).catch((cause: Error) => { if (cause.name !== "AbortError") setError(cause.message); }).finally(() => setLoadingDatasets(false));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!request.dataset_id) return;
    const controller = new AbortController();
    void getSeriesDimensions(request.dataset_id, controller.signal).then((next) => {
      const query = queryRef.current;
      const product = query?.get("product");
      const location = query?.get("location");
      const category = query?.get("category");
      const frequency = query?.get("frequency");
      const selectedFrequency = next.available_frequencies.includes(frequency as ForecastRequest["frequency"])
        ? frequency as ForecastRequest["frequency"]
        : "auto";
      const resolvedFrequency = selectedFrequency === "auto" || selectedFrequency === "original"
        ? next.source_frequency
        : selectedFrequency;
      setDimensions(next);
      setLoadingPreflight(true);
      setRequest((current) => ({
        ...current,
        product: product && next.products.some((item) => item.value === product) ? product : next.products[0]?.value ?? null,
        location: location && next.locations.some((item) => item.value === location) ? location : next.locations[0]?.value ?? null,
        category: category && next.categories.some((item) => item.value === category) ? category : null,
        frequency: selectedFrequency,
        horizon: resolvedFrequency === "daily" ? 30 : 12,
      }));
      queryRef.current = null;
    }).catch((cause: Error) => { if (cause.name !== "AbortError") setError(cause.message); });
    return () => controller.abort();
  }, [request.dataset_id]);

  useEffect(() => {
    if (!dimensions || dimensions.dataset_id !== request.dataset_id) return;
    const controller = new AbortController();
    void getForecastPreflight(request, controller.signal).then((result) => { setPreflight(result); setError(null); }).catch((cause: Error) => { if (cause.name !== "AbortError") setError(cause.message); }).finally(() => { if (!controller.signal.aborted) setLoadingPreflight(false); });
    return () => controller.abort();
  }, [dimensions, request]);

  useEffect(() => {
    if (!dimensions || dimensions.dataset_id !== request.dataset_id) return;
    const controller = new AbortController();
    void getRelevantSignalsForSeries(request.dataset_id, request, controller.signal)
      .then((items) => setContextSignalCount(items.length))
      .catch((cause: Error) => { if (cause.name !== "AbortError") setContextSignalCount(0); });
    return () => controller.abort();
  }, [dimensions, request]);

  const activeDataset = useMemo(() => datasets.find((item) => item.id === request.dataset_id) ?? null, [datasets, request.dataset_id]);
  const champion = run?.models.find((model) => model.rank === 1) ?? null;
  const contextRadarUrl = useMemo(() => {
    const parameters = new URLSearchParams({ dataset_id: request.dataset_id });
    if (request.product) parameters.set("product", request.product);
    if (request.location) parameters.set("location", request.location);
    if (request.category) parameters.set("category", request.category);
    return `/context-radar?${parameters.toString()}`;
  }, [request]);

  function updateRequest(patch: Partial<ForecastRequest>) {
    setError(null);
    setContextSignalCount(null);
    setRun(null);
    setPreflight(null);
    setLoadingPreflight(true);
    if (patch.dataset_id && patch.dataset_id !== request.dataset_id) setDimensions(null);
    setRequest((current) => {
      const next = { ...current, ...patch };
      if (patch.frequency && patch.frequency !== current.frequency) {
        const resolved = patch.frequency === "auto" || patch.frequency === "original" ? dimensions?.source_frequency : patch.frequency;
        next.horizon = resolved === "daily" ? 30 : 12;
      }
      return next;
    });
  }

  async function execute() {
    setRunning(true);
    setError(null);
    try {
      const result = await createForecastRun(request);
      setRun(result);
      setSelectedModel(result.models.find((model) => model.rank === 1) ?? result.models[0] ?? null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : ui.forecastLab.error);
    } finally {
      setRunning(false);
    }
  }

  return <div className="workspace fx-workspace"><header className="workspace-header fx-header"><div><span className="eyebrow">{ui.forecastLab.header.eyebrow}</span><h1>{ui.forecastLab.header.title}</h1><p>{ui.forecastLab.header.subtitle}</p></div>{activeDataset && <div className="fx-active-dataset"><Database size={16} /><span><small>{ui.demandExplorer.header.activeDataset}</small><strong>{activeDataset.name}</strong></span>{preflight && <div className="fx-active-cutoffs"><i>{ui.forecastLab.header.cutoff}: {formatSeriesDate(preflight.data_cutoff)}</i><i>{ui.forecastLab.header.trainingCutoff}: {formatSeriesDate(preflight.training_cutoff)}</i></div>}</div>}</header>
    {loadingDatasets && <div className="fx-page-loading"><RefreshCw size={18} />{ui.demandExplorer.loading}</div>}
    {!loadingDatasets && datasets.length === 0 && <section className="fx-empty"><FlaskConical size={30} /><h2>{ui.forecastLab.empty.title}</h2><p>{ui.forecastLab.empty.description}</p><Link href="/data-studio" className="dx-primary-action">{ui.forecastLab.empty.action}</Link></section>}
    {!loadingDatasets && dimensions && <><ForecastSelector datasets={datasets} dimensions={dimensions} request={request} disabled={running} onChange={updateRequest} /><div className="fx-context-notice"><Radar size={15} /><span>{contextSignalCount !== null && <strong>{ui.forecastLab.header.relevantSignals.replace("{count}", String(contextSignalCount))}</strong>}{ui.forecastLab.header.contextBoundary}</span><Link href={contextRadarUrl}>{ui.forecastLab.header.openContextRadar}</Link></div><PreflightPanel preflight={preflight} loading={loadingPreflight} />{error && <div className="ds-error-message">{error}</div>}<section className="fx-run-zone"><button type="button" disabled={running || loadingPreflight || !preflight} onClick={() => void execute()}>{running ? <RefreshCw size={17} /> : <FlaskConical size={17} />}{running ? ui.forecastLab.run.running : ui.forecastLab.run.action}</button>{running && <div className="fx-run-stages">{ui.forecastLab.run.stages.map((stage) => <span key={stage}>{stage}</span>)}</div>}<small>{ui.forecastLab.run.syncNote}</small></section>
      {run && run.status === "failed" && <div className="ds-error-message">{ui.forecastLab.run.failed}</div>}
      {run && champion && <><ChampionCard run={run} champion={champion} /><div className="fx-context-notice"><BrainCircuit size={15} /><span><strong>{ui.decisionCenter.links.fromForecast}</strong>Las recomendaciones usarán este Forecast Run sin modificarlo.</span><Link href={`/decision-center?forecast_run_id=${run.id}`}>{ui.decisionCenter.links.fromForecast}</Link></div><Leaderboard models={run.models} frequency={run.frequency} selectedId={selectedModel?.id ?? null} onSelect={setSelectedModel} /><ForecastChart run={run} /><div className="fx-audit-grid"><ModelDetail model={selectedModel} /><BacktestingView model={selectedModel ?? champion} /></div><p className="fx-disclaimer">{ui.forecastLab.disclaimer}</p></>}
    </>}
  </div>;
}
