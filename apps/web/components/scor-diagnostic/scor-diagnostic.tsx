"use client";

import { Calculator, Database, FileWarning, Plus, RefreshCw, Route, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ScorAssessmentForm } from "@/components/scor-diagnostic/assessment-form";
import { ScorMetricDetail } from "@/components/scor-diagnostic/metric-detail";
import { ScorMetricMatrix } from "@/components/scor-diagnostic/metric-matrix";
import { ScorProcessMap } from "@/components/scor-diagnostic/process-map";
import {
  applyScorBenchmark,
  calculateScorAssessment,
  createScorAssessment,
  getScorAssessment,
  listScorAssessments,
  listScorDefinitions,
  listScorProfiles,
  regenerateScorDemo,
} from "@/lib/scor-api";
import type {
  ScorAssessment,
  ScorAssessmentSummary,
  ScorBenchmarkProfile,
  ScorDefinition,
  ScorMetricInputDraft,
  ScorMetricResult,
  ScorProcess,
} from "@/lib/scor-types";
import { ui } from "@/lib/i18n";

function percent(value: number | undefined) {
  return value == null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function dateOnly(value: string) {
  return new Date(value).toLocaleDateString("es-PE", { timeZone: "UTC" });
}

function warningLabel(code: string) {
  const labels: Record<string, string> = {
    denominator_zero: "El denominador es cero; el KPI conserva evidencia insuficiente.",
    missing_currency: "Falta declarar la moneda.",
    declared_not_applicable: "Un KPI fue declarado no aplicable.",
    six_complete_months_required: "Se requieren seis meses completos.",
    incompatible_or_missing_time_unit: "Falta una unidad de tiempo compatible.",
    missing_complete_pof_component: "POF requiere D01, D02, D03 y D04 completos.",
  };
  if (code.startsWith("missing_input:")) return `Falta el dato base ${code.split(":")[1]}.`;
  return labels[code] ?? code.replaceAll("_", " ");
}

export function ScorDiagnostic() {
  const copy = ui.scorDiagnostic;
  const [definitions, setDefinitions] = useState<ScorDefinition[]>([]);
  const [assessments, setAssessments] = useState<ScorAssessmentSummary[]>([]);
  const [profiles, setProfiles] = useState<ScorBenchmarkProfile[]>([]);
  const [assessment, setAssessment] = useState<ScorAssessment | null>(null);
  const [selectedProcess, setSelectedProcess] = useState<ScorProcess | "ALL">("ALL");
  const [selectedMetric, setSelectedMetric] = useState<ScorMetricResult | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([listScorDefinitions(), listScorAssessments(), listScorProfiles()])
      .then(async ([definitionItems, assessmentItems, profileItems]) => {
        if (!active) return;
        setDefinitions(definitionItems);
        setAssessments(assessmentItems);
        setProfiles(profileItems);
        const requestedId = new URLSearchParams(window.location.search).get("assessment_id");
        const preferred = assessmentItems.find((item) => item.id === requestedId) ?? assessmentItems[0];
        if (preferred) {
          const detail = await getScorAssessment(preferred.id);
          if (active) setAssessment(detail);
        }
      })
      .catch((cause: Error) => active && setError(cause.message))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  const definitionMap = useMemo(
    () => Object.fromEntries(definitions.map((item) => [item.id, item])),
    [definitions],
  );
  const activeProfile = profiles.find((item) => item.id === assessment?.benchmark_profile_id) ?? null;
  const rankedProcesses = Array.isArray(assessment?.criticality.process_scores)
    ? assessment.criticality.process_scores as Array<Record<string, unknown>>
    : [];

  async function refreshLists(selectedId?: string) {
    const [assessmentItems, profileItems] = await Promise.all([
      listScorAssessments(), listScorProfiles(),
    ]);
    setAssessments(assessmentItems);
    setProfiles(profileItems);
    const id = selectedId ?? assessmentItems[0]?.id;
    if (id) setAssessment(await getScorAssessment(id));
  }

  async function openAssessment(id: string) {
    setWorking(true);
    try {
      const detail = await getScorAssessment(id);
      setAssessment(detail);
      setSelectedMetric(detail.metrics[0] ?? null);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy.error);
    } finally { setWorking(false); }
  }

  async function regenerateDemo() {
    setWorking(true);
    try {
      const result = await regenerateScorDemo();
      await refreshLists(result.assessment.id);
      setSelectedMetric(result.assessment.metrics[0] ?? null);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy.error);
    } finally { setWorking(false); }
  }

  async function calculate() {
    if (!assessment) return;
    setWorking(true);
    try {
      const result = await calculateScorAssessment(assessment.id);
      setAssessment(result);
      setSelectedMetric(result.metrics[0] ?? null);
      await refreshLists(result.id);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy.error);
    } finally { setWorking(false); }
  }

  async function applyProfile(profileId: string) {
    if (!assessment || !profileId) return;
    setWorking(true);
    try {
      const result = await applyScorBenchmark(assessment.id, profileId);
      setAssessment(result);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy.error);
    } finally { setWorking(false); }
  }

  async function create(input: {
    name: string; companyName: string; periodStart: string; periodEnd: string;
    cutoff: string; sourceName: string; metricInputs: ScorMetricInputDraft[];
  }) {
    setWorking(true);
    try {
      const result = await createScorAssessment(input);
      setFormOpen(false);
      await refreshLists(result.id);
      setSelectedMetric(null);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy.error);
    } finally { setWorking(false); }
  }

  if (loading) return <div className="workspace sd-workspace"><div className="sd-loading"><RefreshCw size={18} />{copy.loading}</div></div>;

  return (
    <div className="workspace sd-workspace">
      <header className="workspace-header sd-header"><div><span className="eyebrow">{copy.header.eyebrow}</span><h1>{copy.header.title}</h1><p>{copy.header.subtitle}</p></div><div className="sd-boundary"><ShieldCheck size={18} /><span>{copy.header.boundary}<strong>{copy.header.noOptimization}</strong></span></div></header>
      {error && <div className="ds-error-message">{error}</div>}
      <section className="sd-panel">
        <div className="sd-heading"><div><span>{copy.scope.index}</span><h2>{copy.scope.title}</h2></div><div className="sd-actions"><button type="button" onClick={() => setFormOpen(true)}><Plus size={15} />{copy.scope.new}</button><button type="button" disabled={working} onClick={() => void regenerateDemo()}><Database size={15} />{copy.scope.demo}</button><button className="sd-primary" type="button" disabled={working || !assessment} onClick={() => void calculate()}><Calculator size={15} />{working ? copy.scope.calculating : copy.scope.calculate}</button>{assessment?.status === "calculated" && <Link className="sd-decision-link" href={`/decision-center?scor_assessment_id=${assessment.id}`}>{copy.scope.openDecisions}</Link>}</div></div>
        <div className="sd-scope-grid">
          <label><span>{copy.scope.assessment}</span><select value={assessment?.id ?? ""} disabled={working || !assessments.length} onChange={(event) => void openAssessment(event.target.value)}>{!assessments.length && <option value="">Sin diagnósticos</option>}{assessments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <div><span>{copy.scope.company}</span><strong>{assessment?.company_name ?? "—"}</strong></div>
          <div><span>{copy.scope.period}</span><strong>{assessment ? `${dateOnly(assessment.period_start)} — ${dateOnly(assessment.period_end)}` : "—"}</strong></div>
          <div><span>{copy.scope.cutoff}</span><strong>{assessment ? new Date(assessment.cutoff).toLocaleString("es-PE") : "—"}</strong></div>
          <div><span>{copy.scope.source}</span><strong>{assessment?.source_name ?? "—"}</strong></div>
          <label><span>{copy.scope.benchmark}</span><select value={assessment?.benchmark_profile_id ?? ""} disabled={!assessment || working} onChange={(event) => void applyProfile(event.target.value)}><option value="">{copy.scope.noBenchmark}</option>{profiles.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <div><span>{copy.scope.status}</span><strong>{assessment ? copy.status[assessment.status as keyof typeof copy.status] ?? assessment.status : "—"}</strong></div>
        </div>
        <p className="sd-notice">{copy.scope.notice}</p>
      </section>
      {!assessment && <section className="sd-empty"><Route size={28} /><h2>{copy.empty.title}</h2><p>{copy.empty.description}</p></section>}
      {assessment && <>
        <ScorProcessMap processes={assessment.processes} selected={selectedProcess} onSelect={setSelectedProcess} />
        <ScorMetricMatrix metrics={assessment.metrics} definitions={definitions} process={selectedProcess} selectedId={selectedMetric?.metric_id ?? null} onSelect={setSelectedMetric} />
        <ScorMetricDetail assessment={assessment} metric={selectedMetric} definition={selectedMetric ? definitionMap[selectedMetric.metric_id] ?? null : null} />
        <section className="sd-panel sd-criticality"><div className="sd-heading"><div><span>{copy.criticality.index}</span><h2>{copy.criticality.title}</h2></div>{activeProfile && <small>{activeProfile.name}</small>}</div>{assessment.criticality.status === "insufficient_evidence" ? <div className="sd-critical-empty"><FileWarning size={22} /><p>{copy.criticality.insufficient}</p></div> : <><div className="sd-critical-callout"><span>{assessment.criticality.status === "tie" ? copy.criticality.tie : copy.criticality.candidate}</span><strong>{assessment.criticality.status === "tie" ? (assessment.criticality.tied_processes as string[]).join(" · ") : ui.scorDiagnostic.process[assessment.criticality.selected_process as ScorProcess]}</strong></div><ol>{rankedProcesses.map((item) => <li key={String(item.process)}><b>{String(item.process)}</b><span>{Number(item.weighted_gap_score).toFixed(1)} / 100</span><small>{copy.criticality.coverage}: {percent(Number(item.benchmark_coverage))}</small></li>)}</ol><p>{copy.criticality.disclaimer}</p></>}</section>
        <section className="sd-panel"><div className="sd-heading"><div><span>{copy.audit.index}</span><h2>{copy.audit.title}</h2></div><small>{assessment.algorithm_version}</small></div><div className="sd-audit-grid"><div><span>{copy.audit.total}</span><b>{assessment.summary.metrics_total ?? 0}</b></div><div><span>{copy.audit.complete}</span><b>{assessment.summary.metrics_complete ?? 0}</b></div><div><span>{copy.audit.insufficient}</span><b>{assessment.summary.metrics_insufficient ?? 0}</b></div><div><span>{copy.audit.notApplicable}</span><b>{assessment.summary.metrics_not_applicable ?? 0}</b></div><div><span>{copy.audit.dataCoverage}</span><b>{percent(assessment.summary.data_coverage)}</b></div><div><span>{copy.audit.benchmarkCoverage}</span><b>{percent(assessment.summary.benchmark_coverage)}</b></div><div><span>{copy.audit.calculated}</span><b>{assessment.calculated_at ? new Date(assessment.calculated_at).toLocaleString("es-PE") : "—"}</b></div><div><span>{copy.audit.forecast}</span><b>{assessment.forecast_run_id ?? "No asociado"}</b></div></div>{assessment.warnings.length > 0 && <div className="sd-warnings"><strong>{copy.audit.warnings}</strong><ul>{assessment.warnings.map((item) => <li key={item}>{warningLabel(item)}</li>)}</ul></div>}</section>
      </>}
      {formOpen && <ScorAssessmentForm definitions={definitions} saving={working} onClose={() => setFormOpen(false)} onCreate={(input) => void create(input)} />}
    </div>
  );
}
