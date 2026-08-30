"use client";

import { Archive, FlaskConical, Play, RefreshCw, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AssumptionBuilder } from "@/components/scenario-lab/assumption-builder";
import { ScenarioChart } from "@/components/scenario-lab/scenario-chart";
import { ScenarioSummary } from "@/components/scenario-lab/scenario-summary";
import { getForecastRun } from "@/lib/forecast-api";
import type { ForecastRun } from "@/lib/forecast-types";
import { ui, translateFrequency } from "@/lib/i18n";
import {
  createScenario,
  executeScenario,
  getScenario,
  getScenarioPreflight,
  listForecastRuns,
  listScenarios,
} from "@/lib/scenario-api";
import type {
  ForecastRunSummary,
  ScenarioAssumptionDraft,
  ScenarioPreflight,
  ScenarioRun,
  ScenarioRunSummary,
} from "@/lib/scenario-types";

const initialAssumption: ScenarioAssumptionDraft = {
  clientId: "assumption-1",
  assumption_type: "demand_percent",
  label: "Cambio esperado declarado",
  start_at: "",
  end_at: "",
  magnitude: 0.08,
};

function displayDate(value: string) {
  return new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
}

export function ScenarioLab() {
  const copy = ui.scenarioLab;
  const [forecastRuns, setForecastRuns] = useState<ForecastRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [preflight, setPreflight] = useState<ScenarioPreflight | null>(null);
  const [forecast, setForecast] = useState<ForecastRun | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioRunSummary[]>([]);
  const [scenario, setScenario] = useState<ScenarioRun | null>(null);
  const [assumptions, setAssumptions] = useState<ScenarioAssumptionDraft[]>([initialAssumption]);
  const [name, setName] = useState("Escenario operativo");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([listForecastRuns(), listScenarios()])
      .then(([runs, stored]) => {
        if (!active) return;
        const completed = runs.filter((item) => item.status === "completed");
        setForecastRuns(completed);
        setScenarios(stored);
        setSelectedRunId(completed[0]?.id ?? "");
      })
      .catch((cause: Error) => active && setError(cause.message))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selectedRunId) return;
    let active = true;
    Promise.all([getScenarioPreflight(selectedRunId), getForecastRun(selectedRunId)])
      .then(([flight, run]) => {
        if (!active) return;
        setPreflight(flight);
        setForecast(run);
        const first = flight.baseline_points[0]?.timestamp ?? "";
        const last = flight.baseline_points.at(-1)?.timestamp ?? first;
        setAssumptions([{ ...initialAssumption, start_at: first, end_at: last }]);
      })
      .catch((cause: Error) => active && setError(cause.message));
    return () => { active = false; };
  }, [selectedRunId]);

  const scope = useMemo(() => {
    if (!preflight) return {};
    return Object.fromEntries(
      ["product", "location", "category"]
        .map((key) => [key, preflight.selection[key]])
        .filter((entry): entry is [string, string] => typeof entry[1] === "string"),
    );
  }, [preflight]);

  async function execute() {
    if (!preflight) return;
    setRunning(true);
    setError(null);
    try {
      const created = await createScenario({
        forecastRunId: preflight.forecast_run_id,
        name,
        description,
        frequency: preflight.frequency,
        scope,
        assumptions,
      });
      const result = await executeScenario(created.id);
      setScenario(result);
      setScenarios(await listScenarios());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy.error);
    } finally {
      setRunning(false);
    }
  }

  async function openStored(item: ScenarioRunSummary) {
    setRunning(true);
    setError(null);
    try {
      const [stored, source] = await Promise.all([getScenario(item.id), getForecastRun(item.forecast_run_id)]);
      setSelectedRunId(item.forecast_run_id);
      setForecast(source);
      setScenario(stored);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy.error);
    } finally {
      setRunning(false);
    }
  }

  if (loading) return <div className="workspace sx-workspace"><div className="sx-loading"><RefreshCw size={18} />Cargando contratos de simulación…</div></div>;
  if (!forecastRuns.length) return <div className="workspace sx-workspace"><header className="workspace-header"><div><span className="eyebrow">{copy.header.eyebrow}</span><h1>{copy.header.title}</h1><p>{copy.header.subtitle}</p></div></header><section className="sx-empty"><FlaskConical size={30} /><h2>{copy.empty.title}</h2><p>{copy.empty.description}</p><Link href="/forecast-lab" className="dx-primary-action">{copy.empty.action}</Link></section></div>;

  const valid = assumptions.length > 0 && assumptions.every((item) => item.label.trim() && item.start_at && Number.isFinite(item.magnitude) && (item.assumption_type !== "context_impact" || item.context_impact_estimate_id));
  return (
    <div className="workspace sx-workspace">
      <header className="workspace-header sx-header"><div><span className="eyebrow">{copy.header.eyebrow}</span><h1>{copy.header.title}</h1><p>{copy.header.subtitle}</p></div><div className="sx-boundary"><ShieldCheck size={17} /><span>Baseline oficial intacto<strong>Simulación no causal</strong></span></div></header>
      <section className="sx-panel">
        <div className="sx-heading"><div><span>{copy.baseline.index}</span><h2>{copy.baseline.title}</h2></div><small>{copy.baseline.immutable}</small></div>
        <div className="sx-baseline-grid">
          <label><span>{copy.baseline.select}</span><select value={selectedRunId} disabled={running} onChange={(event) => { setPreflight(null); setForecast(null); setScenario(null); setSelectedRunId(event.target.value); }}>{forecastRuns.map((run) => <option key={run.id} value={run.id}>{run.data_cutoff} · {translateFrequency(run.frequency)} · {run.champion_model}</option>)}</select></label>
          <div><span>{copy.baseline.champion}</span><strong>{preflight?.champion_model ?? "—"}</strong></div>
          <div><span>{copy.baseline.horizon}</span><strong>{preflight?.horizon ?? "—"}</strong></div>
          <div><span>{copy.baseline.frequency}</span><strong>{preflight ? translateFrequency(preflight.frequency) : "—"}</strong></div>
          <div><span>{copy.baseline.cutoff}</span><strong>{preflight ? displayDate(preflight.data_cutoff) : "—"}</strong></div>
        </div>
      </section>
      {preflight && <>
        <section className="sx-panel sx-meta-form"><label><span>{copy.builder.scenarioName}</span><input value={name} maxLength={160} disabled={running} onChange={(event) => setName(event.target.value)} /></label><label><span>{copy.builder.scenarioDescription}</span><input value={description} maxLength={2000} disabled={running} onChange={(event) => setDescription(event.target.value)} /></label></section>
        <AssumptionBuilder assumptions={assumptions} evidence={preflight.eligible_context_impacts} disabled={running} onChange={setAssumptions} />
        {error && <div className="ds-error-message">{error}</div>}
        <section className="sx-run"><button type="button" disabled={running || !valid || !name.trim()} onClick={() => void execute()}>{running ? <RefreshCw size={16} /> : <Play size={16} />}{running ? copy.builder.executing : copy.builder.execute}</button><p>{copy.builder.disclaimer}</p></section>
      </>}
      {scenario && forecast && <section className="sx-panel"><div className="sx-heading"><div><span>{copy.result.index}</span><h2>{scenario.name}</h2></div><strong>{scenario.status === "completed" ? "SIMULACIÓN COMPLETADA" : scenario.status}</strong></div><ScenarioSummary scenario={scenario} /><ScenarioChart forecast={forecast} scenario={scenario} /><div className="sx-assumption-ledger">{scenario.assumptions.map((item) => <article key={item.id}><span>{item.order_index + 1}</span><div><strong>{item.label}</strong><small>{item.source_type === "historical_evidence" ? copy.builder.evidenceBadge : copy.builder.manualBadge} · {item.start_at.slice(0, 10)} → {(item.end_at ?? item.start_at).slice(0, 10)}</small></div><b>{item.unit === "absolute" ? item.magnitude : `${((item.magnitude ?? 0) * 100).toFixed(1)}%`}</b></article>)}</div></section>}
      <section className="sx-panel"><div className="sx-heading"><div><span>{copy.previous.index}</span><h2>{copy.previous.title}</h2></div><Archive size={17} /></div>{!scenarios.length ? <p className="sx-muted">{copy.previous.empty}</p> : <div className="sx-history">{scenarios.map((item) => <button type="button" key={item.id} disabled={running} onClick={() => void openStored(item)}><span><strong>{item.name}</strong><small>{displayDate(item.created_at.slice(0, 10))} · {translateFrequency(item.frequency)} · {item.champion_model}</small></span><b>{item.total_relative_delta == null ? "—" : `${item.total_relative_delta >= 0 ? "+" : ""}${(item.total_relative_delta * 100).toFixed(1)}%`}</b></button>)}</div>}</section>
    </div>
  );
}
