import { apiRequest } from "@/lib/api-client";
import type {
  ReadyDatasetSummary,
  SeriesDimensions,
  SeriesFilters,
  SeriesProfile,
} from "@/lib/series-types";

export function getReadyDatasets(signal?: AbortSignal): Promise<ReadyDatasetSummary[]> {
  return apiRequest("/api/v1/series/datasets", { signal });
}

export function getSeriesDimensions(
  datasetId: string,
  signal?: AbortSignal,
): Promise<SeriesDimensions> {
  return apiRequest(`/api/v1/series/datasets/${datasetId}/dimensions`, { signal });
}

export function getSeriesProfile(filters: SeriesFilters, signal?: AbortSignal): Promise<SeriesProfile> {
  const parameters = new URLSearchParams();
  if (filters.product) parameters.set("product", filters.product);
  if (filters.location) parameters.set("location", filters.location);
  if (filters.category) parameters.set("category", filters.category);
  if (filters.startDate) parameters.set("start_date", filters.startDate);
  if (filters.endDate) parameters.set("end_date", filters.endDate);
  parameters.set("frequency", filters.frequency);
  return apiRequest(
    `/api/v1/series/datasets/${filters.datasetId}/profile?${parameters.toString()}`,
    { signal },
  );
}
