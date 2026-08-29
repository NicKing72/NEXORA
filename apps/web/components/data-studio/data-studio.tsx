"use client";

import { useState } from "react";

import { ImportStep } from "@/components/data-studio/import-step";
import { MapStep } from "@/components/data-studio/map-step";
import { ReadyStep } from "@/components/data-studio/ready-step";
import { ValidateStep } from "@/components/data-studio/validate-step";
import { WorkflowStepper } from "@/components/data-studio/workflow-stepper";
import { createDemoDataset, getDataset, getPreview, markReady, saveMappings, selectDatasetSheet, uploadDataset, validateDataset } from "@/lib/data-studio-api";
import type { ColumnMapping, Dataset, DatasetPreview, OperationState, QualityAssessment, ReadyPayload, WorkflowStep } from "@/lib/data-studio-types";
import { ui } from "@/lib/i18n";

export function DataStudio() {
  const [step, setStep] = useState<WorkflowStep>("import");
  const [state, setState] = useState<OperationState>("idle");
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [selectedSheet, setSelectedSheet] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [mappings, setMappings] = useState<ColumnMapping[]>([]);
  const [assessment, setAssessment] = useState<QualityAssessment | null>(null);
  const [readyPayload, setReadyPayload] = useState<ReadyPayload | null>(null);

  async function prepareMapping(nextDataset: Dataset) {
    const nextPreview = await getPreview(nextDataset.id);
    setDataset(nextDataset);
    setPreview(nextPreview);
    setMappings(nextDataset.mappings);
    setState("success");
    setStep("map");
  }

  async function acceptDataset(task: Promise<Dataset>) {
    setError(null);
    try {
      const nextDataset = await task;
      setDataset(nextDataset);
      if (nextDataset.status === "awaiting_sheet") {
        setSelectedSheet(nextDataset.available_sheets[0] ?? "");
        setState("warning");
        return;
      }
      setState("processing");
      await prepareMapping(nextDataset);
    } catch (cause) {
      setState("error");
      setError(cause instanceof Error ? cause.message : ui.dataStudio.errors.datasetProcessing);
    }
  }

  function assignRole(role: string, columnName: string) {
    setMappings((current) => current.map((mapping) => {
      if (mapping.role === role) return { ...mapping, role: "ignore", source: "manual", confidence: 1 };
      if (mapping.column_name === columnName) return { ...mapping, role, source: "manual", confidence: 1 };
      return mapping;
    }));
  }

  async function saveAndValidate() {
    if (!dataset) return;
    setState("processing");
    setError(null);
    try {
      const saved = await saveMappings(dataset.id, mappings.map(({ column_name, role }) => ({ column_name, role })));
      setMappings(saved);
      const result = await validateDataset(dataset.id);
      setAssessment(result);
      setDataset(await getDataset(dataset.id));
      setState(result.report.has_critical_errors ? "warning" : "success");
      setStep("validate");
    } catch (cause) {
      setState("error");
      setError(cause instanceof Error ? cause.message : ui.dataStudio.errors.mappingValidation);
    }
  }

  async function rerunValidation() {
    if (!dataset) return;
    setState("processing");
    setError(null);
    try {
      const result = await validateDataset(dataset.id);
      setAssessment(result);
      setState(result.report.has_critical_errors ? "warning" : "success");
    } catch (cause) {
      setState("error");
      setError(cause instanceof Error ? cause.message : ui.dataStudio.errors.validation);
    }
  }

  async function completeReady() {
    if (!dataset) return;
    setState("processing");
    setError(null);
    try {
      const result = await markReady(dataset.id);
      setReadyPayload(result);
      setDataset(result.dataset);
      setState("success");
      setStep("ready");
    } catch (cause) {
      setState("error");
      setError(cause instanceof Error ? cause.message : ui.dataStudio.errors.markReady);
    }
  }

  return (
    <div className="workspace ds-workspace">
      <header className="workspace-header ds-header">
        <div>
          <span className="eyebrow">{ui.dataStudio.header.eyebrow}</span>
          <h1>{ui.dataStudio.header.title}</h1>
          <p>{ui.dataStudio.header.subtitle}</p>
        </div>
        <span className="ds-local-badge"><i /> {ui.dataStudio.header.local}</span>
      </header>

      <WorkflowStepper current={step} />

      {step === "import" && (
        <ImportStep
          state={state}
          dataset={dataset}
          selectedSheet={selectedSheet}
          error={error}
          onFile={(file) => { setState("uploading"); void acceptDataset(uploadDataset(file)); }}
          onDemo={() => { setState("processing"); void acceptDataset(createDemoDataset()); }}
          onSheetChange={setSelectedSheet}
          onSheetConfirm={() => {
            if (!dataset || !selectedSheet) return;
            setState("processing");
            void acceptDataset(selectDatasetSheet(dataset.id, selectedSheet));
          }}
          onDragState={(dragging) => setState(dragging ? "dragging" : "idle")}
        />
      )}
      {step === "map" && dataset && preview && (
        <MapStep
          dataset={dataset}
          preview={preview}
          mappings={mappings}
          state={state}
          error={error}
          onAssign={assignRole}
          onClassifyUnassigned={(column, role) => setMappings((current) => current.map((mapping) => mapping.column_name === column ? { ...mapping, role, source: "manual", confidence: 1 } : mapping))}
          onBack={() => { setStep("import"); setState("idle"); setError(null); }}
          onContinue={() => void saveAndValidate()}
        />
      )}
      {step === "validate" && assessment && (
        <ValidateStep
          assessment={assessment}
          state={state}
          error={error}
          onBack={() => { setStep("map"); setError(null); }}
          onRerun={() => void rerunValidation()}
          onReady={() => void completeReady()}
        />
      )}
      {step === "ready" && readyPayload && <ReadyStep payload={readyPayload} onReview={() => setStep("validate")} />}
    </div>
  );
}
