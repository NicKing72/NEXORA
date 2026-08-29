"use client";

import { Database, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { DemandChart, type EventVisibility } from "@/components/demand-explorer/demand-chart";
import { ExplorerEmptyState } from "@/components/demand-explorer/explorer-empty-state";
import { PatternInsights } from "@/components/demand-explorer/pattern-insights";
import { SeriesSelector } from "@/components/demand-explorer/series-selector";
import { SeriesStatistics } from "@/components/demand-explorer/series-statistics";
import { getReadyDatasets, getSeriesDimensions, getSeriesProfile } from "@/lib/series-api";
import type { EventCounts, ReadyDatasetSummary, SeriesDimensions, SeriesFilters, SeriesProfile } from "@/lib/series-types";
import { interpolate, ui } from "@/lib/i18n";

const INITIAL_FILTERS: SeriesFilters = {
  datasetId: "",
  product: "",
  location: "",
  category: "",
  frequency: "auto",
  startDate: "",
  endDate: "",
};

export function DemandExplorer() {
  const [datasets, setDatasets] = useState<ReadyDatasetSummary[]>([]);
  const [dimensions, setDimensions] = useState<SeriesDimensions | null>(null);
  const [filters, setFilters] = useState<SeriesFilters>(INITIAL_FILTERS);
  const [profile, setProfile] = useState<SeriesProfile | null>(null);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visibility, setVisibility] = useState<EventVisibility>({
    outlier: true,
    missing: true,
    stockout: true,
    zero: false,
  });

  useEffect(() => {
    const controller = new AbortController();
    void getReadyDatasets(controller.signal)
      .then((items) => {
        setDatasets(items);
        setLoadingProfile(items.length > 0);
        setFilters((current) => ({ ...current, datasetId: current.datasetId || items[0]?.id || "" }));
        setError(null);
      })
      .catch((cause: Error) => {
        if (cause.name !== "AbortError") setError(cause.message);
      })
      .finally(() => setLoadingDatasets(false));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!filters.datasetId) return;
    const controller = new AbortController();
    void getSeriesDimensions(filters.datasetId, controller.signal)
      .then((next) => {
        setDimensions(next);
        setFilters((current) => ({
          ...current,
          product: next.products[0]?.value ?? "",
          location: next.locations[0]?.value ?? "",
          category: "",
          frequency: "auto",
          startDate: "",
          endDate: "",
        }));
        setError(null);
      })
      .catch((cause: Error) => {
        if (cause.name !== "AbortError") {
          setError(cause.message);
          setLoadingProfile(false);
        }
      });
    return () => controller.abort();
  }, [filters.datasetId]);

  useEffect(() => {
    if (!dimensions || dimensions.dataset_id !== filters.datasetId) return;
    const controller = new AbortController();
    void getSeriesProfile(filters, controller.signal)
      .then((next) => {
        setProfile(next);
        setError(null);
      })
      .catch((cause: Error) => {
        if (cause.name !== "AbortError") setError(cause.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingProfile(false);
      });
    return () => controller.abort();
  }, [dimensions, filters]);

  const activeDataset = useMemo(
    () => datasets.find((dataset) => dataset.id === filters.datasetId) ?? null,
    [datasets, filters.datasetId],
  );

  function updateFilters(patch: Partial<SeriesFilters>) {
    if (patch.datasetId && patch.datasetId !== filters.datasetId) {
      setDimensions(null);
      setProfile(null);
    }
    setLoadingProfile(true);
    setFilters((current) => ({ ...current, ...patch }));
  }

  function toggleEvent(event: keyof EventCounts, visible: boolean) {
    setVisibility((current) => ({ ...current, [event]: visible }));
  }

  return (
    <div className="workspace dx-workspace">
      <header className="workspace-header dx-header">
        <div>
          <span className="eyebrow">{ui.demandExplorer.header.eyebrow}</span>
          <h1>{ui.demandExplorer.header.title}</h1>
          <p>{ui.demandExplorer.header.subtitle}</p>
        </div>
        {activeDataset && (
          <div className="dx-active-dataset">
            <Database size={16} />
            <span><small>{ui.demandExplorer.header.activeDataset}</small><strong>{activeDataset.name}</strong></span>
            <i>{interpolate(ui.demandExplorer.header.readiness, { score: activeDataset.readiness_score })}</i>
          </div>
        )}
      </header>

      {loadingDatasets && <div className="dx-loading"><RefreshCw size={18} /> {ui.demandExplorer.loading}</div>}
      {!loadingDatasets && datasets.length === 0 && <ExplorerEmptyState />}
      {!loadingDatasets && datasets.length > 0 && dimensions && (
        <>
          <SeriesSelector datasets={datasets} dimensions={dimensions} filters={filters} isLoading={loadingProfile} onChange={updateFilters} />
          {error && <div className="ds-error-message">{error}</div>}
          {profile && (
            <>
              <div className="dx-profile-status">
                {profile.selection.is_aggregated && <strong>{ui.demandExplorer.selector.aggregated}</strong>}
                {profile.selection.aggregation_note && <span>{ui.demandExplorer.selector.aggregationNotes[profile.selection.aggregation_note as keyof typeof ui.demandExplorer.selector.aggregationNotes]}</span>}
                {profile.selection.price_method && <small>{ui.demandExplorer.priceMethods[profile.selection.price_method as keyof typeof ui.demandExplorer.priceMethods]}</small>}
              </div>
              <DemandChart
                points={profile.points}
                frequency={profile.selection.resolved_frequency}
                visibility={visibility}
                onVisibilityChange={toggleEvent}
              />
              <SeriesStatistics statistics={profile.statistics} />
              <PatternInsights profile={profile} />
            </>
          )}
          {loadingProfile && <div className="dx-profile-loading"><RefreshCw size={16} /> {ui.demandExplorer.loading}</div>}
        </>
      )}
    </div>
  );
}
