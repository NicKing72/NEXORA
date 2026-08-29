import type {
  ColumnMapping,
  Dataset,
  DatasetPreview,
  QualityAssessment,
  ReadyPayload,
} from "@/lib/data-studio-types";
import { apiRequest } from "@/lib/api-client";

export function uploadDataset(file: File): Promise<Dataset> {
  const form = new FormData();
  form.append("file", file);
  return apiRequest("/api/v1/datasets/upload", { method: "POST", body: form });
}

export function createDemoDataset(): Promise<Dataset> {
  return apiRequest("/api/v1/datasets/demo", { method: "POST" });
}

export function selectDatasetSheet(datasetId: string, sheet: string): Promise<Dataset> {
  return apiRequest(`/api/v1/datasets/${datasetId}/sheet`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sheet }),
  });
}

export function getDataset(datasetId: string): Promise<Dataset> {
  return apiRequest(`/api/v1/datasets/${datasetId}`);
}

export function getPreview(datasetId: string): Promise<DatasetPreview> {
  return apiRequest(`/api/v1/datasets/${datasetId}/preview?limit=30`);
}

export function saveMappings(
  datasetId: string,
  mappings: Array<{ column_name: string; role: string }>,
): Promise<ColumnMapping[]> {
  return apiRequest(`/api/v1/datasets/${datasetId}/mappings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mappings }),
  });
}

export function validateDataset(datasetId: string): Promise<QualityAssessment> {
  return apiRequest(`/api/v1/datasets/${datasetId}/validate`, { method: "POST" });
}

export function markReady(datasetId: string): Promise<ReadyPayload> {
  return apiRequest(`/api/v1/datasets/${datasetId}/ready`, { method: "POST" });
}
