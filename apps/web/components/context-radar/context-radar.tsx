"use client";

import { Database, Plus, Radar, RefreshCw, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { ContextFiltersPanel } from "@/components/context-radar/context-filters";
import { ContextSummary } from "@/components/context-radar/context-summary";
import { ContextTimeline } from "@/components/context-radar/context-timeline";
import { RelevanceView } from "@/components/context-radar/relevance-view";
import { SignalDetail } from "@/components/context-radar/signal-detail";
import { SignalForm } from "@/components/context-radar/signal-form";
import { createContextSignal, estimateContextImpact, getContextAnalogies, getContextSignals, getDatasetContextImpacts, getRelevantSignals, regenerateDemoContext, updateContextSignalStatus } from "@/lib/context-api";
import type { ContextAnalogy, ContextFilters, ContextImpactEstimate, ContextSignal, ManualSignalInput, RelevantSignal } from "@/lib/context-types";
import { ui } from "@/lib/i18n";
import { getReadyDatasets, getSeriesDimensions } from "@/lib/series-api";
import type { ReadyDatasetSummary, SeriesDimensions } from "@/lib/series-types";

function toLocalDatetimeInput(date: Date): string {
  const localDate = new Date(date);
  localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset());
  return localDate.toISOString().slice(0, 16);
}

const INITIAL_FILTERS: ContextFilters = { datasetId: "", product: "", location: "", category: "", family: "", status: "", source: "", eventFrom: "", eventTo: "", cutoff: "" };

export function ContextRadar() {
  const [datasets, setDatasets] = useState<ReadyDatasetSummary[]>([]);
  const [dimensions, setDimensions] = useState<SeriesDimensions | null>(null);
  const [filters, setFilters] = useState<ContextFilters>(INITIAL_FILTERS);
  const [signals, setSignals] = useState<ContextSignal[]>([]);
  const [relevant, setRelevant] = useState<RelevantSignal[]>([]);
  const [impacts, setImpacts] = useState<ContextImpactEstimate[]>([]);
  const [analogies, setAnalogies] = useState<ContextAnalogy[]>([]);
  const [selected, setSelected] = useState<ContextSignal | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [estimating, setEstimating] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [referenceTime, setReferenceTime] = useState<number | null>(null);
  const queryRef = useRef<URLSearchParams | null>(null);

  useEffect(() => {
    queryRef.current = new URLSearchParams(window.location.search);
    const controller = new AbortController();
    void getReadyDatasets(controller.signal).then((items) => {
      const requested = queryRef.current?.get("dataset_id");
      const datasetId = items.some((item) => item.id === requested) ? requested! : items[0]?.id ?? "";
      const loadedAt = new Date();
      setDatasets(items);
      setReferenceTime(loadedAt.getTime());
      setFilters((current) => ({
        ...current,
        cutoff: current.cutoff || toLocalDatetimeInput(loadedAt),
        datasetId,
      }));
    }).catch((cause: Error) => { if (cause.name !== "AbortError") setError(cause.message); }).finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!filters.datasetId) return;
    const controller = new AbortController();
    void getSeriesDimensions(filters.datasetId, controller.signal).then((next) => {
      const query = queryRef.current;
      const product = query?.get("product");
      const location = query?.get("location");
      const category = query?.get("category");
      setDimensions(next);
      setFilters((current) => ({ ...current,
        product: product && next.products.some((item) => item.value === product) ? product : "",
        location: location && next.locations.some((item) => item.value === location) ? location : "",
        category: category && next.categories.some((item) => item.value === category) ? category : "",
      }));
      queryRef.current = null;
    }).catch((cause: Error) => { if (cause.name !== "AbortError") setError(cause.message); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [filters.datasetId]);

  useEffect(() => {
    if (!dimensions || dimensions.dataset_id !== filters.datasetId) return;
    const controller = new AbortController();
    void Promise.all([getContextSignals(filters, controller.signal), getRelevantSignals(filters, controller.signal), getDatasetContextImpacts(filters.datasetId, controller.signal)]).then(async ([items, matches, estimates]) => {
      const futureSignals = items.filter((item) => ["known_future", "forecasted_external", "scenario"].includes(item.knowledge_type));
      const analogyResults = await Promise.all(futureSignals.map((item) => getContextAnalogies(item.id, controller.signal)));
      setSignals(items);
      setRelevant(matches);
      setImpacts(estimates);
      setAnalogies(analogyResults);
      setSelected((current) => items.find((item) => item.id === current?.id) ?? items[0] ?? null);
      setError(null);
    }).catch((cause: Error) => { if (cause.name !== "AbortError") setError(cause.message); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [dimensions, filters, revision]);

  const activeDataset = useMemo(() => datasets.find((item) => item.id === filters.datasetId) ?? null, [datasets, filters.datasetId]);
  const visibleIds = useMemo(() => new Set(signals.map((item) => item.id)), [signals]);
  const visibleRelevant = useMemo(() => relevant.filter((item) => visibleIds.has(item.signal.id)), [relevant, visibleIds]);
  const selectedImpact = useMemo(() => impacts.find((item) => item.signal_id === selected?.id) ?? null, [impacts, selected]);
  const selectedAnalogy = useMemo(() => analogies.find((item) => item.signal_id === selected?.id) ?? null, [analogies, selected]);
  const seriesLabel = [filters.product || ui.contextRadar.filters.allProducts, filters.location || ui.contextRadar.filters.allLocations, filters.category].filter(Boolean).join(" · ");

  function updateFilters(patch: Partial<ContextFilters>) {
    if (patch.datasetId && patch.datasetId !== filters.datasetId) { setDimensions(null); setSignals([]); setRelevant([]); setImpacts([]); setAnalogies([]); setSelected(null); }
    setFilters((current) => ({ ...current, ...patch }));
  }

  async function saveSignal(payload: ManualSignalInput) {
    setSaving(true);
    try { await createContextSignal(payload); setFormOpen(false); setRevision((value) => value + 1); setError(null); }
    catch (cause) { setError(cause instanceof Error ? cause.message : ui.contextRadar.errors.create); }
    finally { setSaving(false); }
  }

  async function changeStatus(status: "dismissed" | "reviewed") {
    if (!selected) return;
    try { const updated = await updateContextSignalStatus(selected.id, status); setSelected(updated); setRevision((value) => value + 1); }
    catch (cause) { setError(cause instanceof Error ? cause.message : ui.contextRadar.errors.status); }
  }

  async function loadDemo() {
    if (!filters.datasetId) return;
    setLoading(true);
    try { await regenerateDemoContext(filters.datasetId); setRevision((value) => value + 1); setError(null); }
    catch (cause) { setError(cause instanceof Error ? cause.message : ui.contextRadar.errors.demo); setLoading(false); }
  }

  async function estimateImpact() {
    if (!selected) return;
    setEstimating(true);
    try {
      const result = await estimateContextImpact(selected.id);
      setImpacts((current) => [result, ...current.filter((item) => item.signal_id !== result.signal_id)]);
      setRevision((value) => value + 1);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : ui.contextRadar.errors.load);
    } finally {
      setEstimating(false);
    }
  }

  return <div className="workspace cx-workspace"><header className="workspace-header cx-header"><div><span className="eyebrow">{ui.contextRadar.header.eyebrow}</span><h1>{ui.contextRadar.header.title}</h1><p>{ui.contextRadar.header.subtitle}</p></div><div className="cx-header-actions">{activeDataset && <div className="cx-active-dataset"><Database size={16} /><span><small>{ui.contextRadar.header.activeDataset}</small><strong>{activeDataset.name}</strong><i>{ui.contextRadar.header.univariate}</i></span></div>}{activeDataset?.source_type === "demo" && <button type="button" className="cx-secondary-action" disabled={loading} onClick={() => void loadDemo()}><Sparkles size={15} />{ui.contextRadar.actions.demo}</button>}{dimensions && <button type="button" className="cx-primary-action" onClick={() => setFormOpen(true)}><Plus size={16} />{ui.contextRadar.actions.newSignal}</button>}</div></header>
    {loading && <div className="cx-loading"><RefreshCw size={17} />{ui.contextRadar.loading}</div>}
    {error && <div className="ds-error-message">{error}</div>}
    {!loading && datasets.length === 0 && <section className="cx-no-dataset"><Radar size={30} /><h2>{ui.contextRadar.empty.noDataset}</h2><Link href="/data-studio">{ui.contextRadar.empty.dataStudio}</Link></section>}
    {dimensions && referenceTime !== null && <><ContextSummary signals={signals} impacts={impacts} analogies={analogies} /><ContextFiltersPanel datasets={datasets} dimensions={dimensions} filters={filters} onChange={updateFilters} />
      {signals.length === 0 && activeDataset?.source_type === "demo" && <section className="cx-demo-callout"><Sparkles size={20} /><div><strong>{ui.contextRadar.empty.title}</strong><p>{ui.contextRadar.empty.description}</p></div><button type="button" onClick={() => void loadDemo()}>{ui.contextRadar.actions.demo}</button></section>}
      <ContextTimeline signals={signals} selectedId={selected?.id ?? null} referenceTime={referenceTime} onSelect={setSelected} />
      <div className="cx-intelligence-grid"><SignalDetail signal={selected} impact={selectedImpact} analogy={selectedAnalogy} estimating={estimating} onEstimate={() => void estimateImpact()} onStatus={(status) => void changeStatus(status)} /><RelevanceView matches={visibleRelevant} seriesLabel={seriesLabel} /></div>
    </>}
    {formOpen && dimensions && <SignalForm datasetId={filters.datasetId} dimensions={dimensions} saving={saving} onClose={() => setFormOpen(false)} onSave={saveSignal} />}
  </div>;
}
