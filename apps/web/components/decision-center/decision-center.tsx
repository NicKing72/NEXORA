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
import {
  parseDecisionHandoff,
  resolveDecisionRunHandoff,
  resolveExactSelection,
  type DecisionHandoff,
} from "@/lib/decision-handoff";
import { rememberDecisionWorkspace } from "@/lib/decision-workspace";
import type {
  DecisionPreflight,
  DecisionPortfolioRun,
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

function rate(value: number | null | undefined) {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function dateOnly(value: string) {
  return new Date(value).toLocaleDateString("es-PE", { timeZone: "UTC" });
}

function portfolioOptionLabel(item: DecisionPortfolioRun) {
  const created = new Date(item.created_at).toLocaleString("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  });
  const risk = ui.portfolio.risks[
    item.related_item.risk_level as keyof typeof ui.portfolio.risks
  ] ?? item.related_item.risk_level;
  return [
    item.related_item.product ?? ui.decisionCenter.setup.aggregateSeries,
    item.related_item.location ?? ui.decisionCenter.setup.allLocations,
    risk,
    created,
    `ID ${item.id.slice(0, 8)}`,
  ].join(" · ");
}

export function DecisionCenter() {
  const copy = ui.decisionCenter;
  const [forecasts, setForecasts] = useState<ForecastRunSummary[]>([]);
  const [forecastRunId, setForecastRunId] = useState("");
  const [scenarioRunId, setScenarioRunId] = useState("");
  const [scorAssessmentId, setScorAssessmentId] = useState("");
  const [portfolioRunId, setPortfolioRunId] = useState("");
  const [cutoff, setCutoff] = useState("");
  const [preflight, setPreflight] = useState<DecisionPreflight | null>(null);
  const [runs, setRuns] = useState<DecisionRunSummary[]>([]);
  const [run, setRun] = useState<DecisionRun | null>(null);
  const [selected, setSelected] = useState<DecisionRecommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [portfolioHandoffNotice, setPortfolioHandoffNotice] = useState<string | null>(null);
  const handoffRef = useRef<DecisionHandoff | null>(null);
  const handoffUnavailable = copy.setup.contextHandoffUnavailable;

  useEffect(() => {
    const handoff = parseDecisionHandoff(window.location.search);
    handoffRef.current = handoff;
    let active = true;
    const localCutoff = toLocalInput(new Date());
    const requestedDecision = handoff.decisionRunId
      ? getDecisionRun(handoff.decisionRunId)
          .then((run) => ({ run, unavailable: false }))
          .catch(() => ({ run: null, unavailable: true }))
      : Promise.resolve({ run: null, unavailable: false });
    Promise.all([listDecisionForecasts(), listDecisionRuns(), requestedDecision])
      .then(([forecastItems, runItems, decisionResult]) => {
        if (!active) return;
        const completed = forecastItems.filter((item) => item.status === "completed");
        setForecasts(completed);
        setRuns(runItems);
        if (decisionResult.unavailable) {
          const exactForecast = handoff.forecastRunId
            ? completed.find((item) => item.id === handoff.forecastRunId)
            : null;
          setCutoff(localCutoff);
          setForecastRunId(exactForecast?.id ?? "");
          setError(handoffUnavailable);
          handoffRef.current = null;
          return;
        }
        const storedDecision = decisionResult.run;
        if (storedDecision) {
          const resolved = resolveDecisionRunHandoff(handoff, storedDecision);
          if (!resolved.ok) {
            setCutoff(localCutoff);
            setForecastRunId("");
            setError(handoffUnavailable);
            handoffRef.current = null;
            return;
          }
          setForecastRunId(storedDecision.forecast_run_id);
          setScenarioRunId(storedDecision.scenario_run_id ?? "");
          setScorAssessmentId(storedDecision.scor_assessment_id ?? "");
          setPortfolioRunId(storedDecision.portfolio_run_id ?? "");
          setCutoff(toLocalInput(new Date(storedDecision.decision_cutoff)));
          setRun(storedDecision);
          setSelected(storedDecision.recommendations[0] ?? null);
          handoffRef.current = null;
          return;
        }
        const exactForecast = handoff.forecastRunId
          ? completed.find((item) => item.id === handoff.forecastRunId)
          : null;
        if (handoff.forecastRunId && !exactForecast) {
          setCutoff(localCutoff);
          setForecastRunId("");
          setError(handoffUnavailable);
          handoffRef.current = null;
          return;
        }
        setCutoff(localCutoff);
        setForecastRunId(exactForecast?.id ?? completed[0]?.id ?? "");
      })
      .catch(() => {
        if (active) {
          setError(handoffUnavailable);
          handoffRef.current = null;
        }
      })
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [handoffUnavailable]);

  useEffect(() => {
    if (!forecastRunId || !cutoff) return;
    let active = true;
    const decisionCutoff = new Date(cutoff).toISOString();
    void getDecisionPreflight({
      forecastRunId,
      scenarioRunId,
      scorAssessmentId,
      portfolioRunId,
      decisionCutoff,
    })
      .then((result) => {
        if (!active) return;
        setPreflight(result);
        const pending = handoffRef.current;
        const targetsCurrentForecast = pending
          && !pending.decisionRunId
          && (!pending.forecastRunId || pending.forecastRunId === result.forecast_run_id);
        if (pending && targetsCurrentForecast) {
          const scenario = resolveExactSelection(
            pending.scenarioRunId,
            result.scenarios.map((item) => item.id),
          );
          const scor = resolveExactSelection(
            pending.scorAssessmentId,
            (result.scor_assessments ?? []).map((item) => item.id),
          );
          const portfolio = resolveExactSelection(
            pending.portfolioRunId,
            result.portfolios.map((item) => item.id),
          );
          setScenarioRunId(scenario.value);
          setScorAssessmentId(scor.value);
          setPortfolioRunId(portfolio.value);
          const unavailable = scenario.unavailable || scor.unavailable || portfolio.unavailable;
          setPortfolioHandoffNotice(portfolio.unavailable ? copy.setup.portfolioHandoffUnavailable : null);
          if (unavailable) setError(handoffUnavailable);
          handoffRef.current = null;
        }
        const runMatchesResolvedContext = run
          && run.forecast_run_id === forecastRunId
          && (run.scenario_run_id ?? "") === scenarioRunId
          && (run.scor_assessment_id ?? "") === scorAssessmentId
          && (run.portfolio_run_id ?? "") === portfolioRunId
          && toLocalInput(new Date(run.decision_cutoff)) === cutoff;
        if (runMatchesResolvedContext) rememberDecisionWorkspace(run);
      })
      .catch((cause: Error) => active && setError(cause.message));
    return () => { active = false; };
  }, [forecastRunId, scenarioRunId, scorAssessmentId, portfolioRunId, cutoff, copy.setup.portfolioHandoffUnavailable, handoffUnavailable, run]);

  const activeForecast = useMemo(
    () => forecasts.find((item) => item.id === forecastRunId) ?? null,
    [forecasts, forecastRunId],
  );
  const openCount = run?.recommendations.filter((item) => ["open", "acknowledged", "under_review"].includes(item.status)).length ?? 0;
  const selectedScor = preflight?.selected_scor ?? null;
  const selectedPortfolio = preflight?.selected_portfolio ?? null;
  const portfolioItem = selectedPortfolio?.related_items[0] ?? null;
  const scorTies = Array.isArray(selectedScor?.criticality.tied_processes)
    ? selectedScor.criticality.tied_processes as string[]
    : [];
  const scorCriticality = scorTies.length
    ? scorTies.join(" · ")
    : String(selectedScor?.criticality.selected_process ?? copy.setup.insufficientScor);

  async function analyze() {
    if (!forecastRunId || !cutoff) return;
    setAnalyzing(true);
    setError(null);
    try {
      const result = await createDecisionRun({
        forecastRunId,
        scenarioRunId,
        scorAssessmentId,
        portfolioRunId,
        decisionCutoff: new Date(cutoff).toISOString(),
      });
      setRun(result);
      setSelected(result.recommendations[0] ?? null);
      rememberDecisionWorkspace(result);
      setRuns(await listDecisionRuns());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy.error);
    } finally {
      setAnalyzing(false);
    }
  }

  function selectPortfolio(nextId: string) {
    setPortfolioRunId(nextId);
    setPortfolioHandoffNotice(null);
    handoffRef.current = null;
    const params = new URLSearchParams(window.location.search);
    if (nextId) {
      params.set("portfolio_run_id", nextId);
      params.set("forecast_run_id", forecastRunId);
    } else {
      params.delete("portfolio_run_id");
    }
    const query = params.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
    setRun(null);
    setSelected(null);
  }

  async function openStored(item: DecisionRunSummary) {
    setAnalyzing(true);
    setError(null);
    try {
      const stored = await getDecisionRun(item.id);
      setForecastRunId(stored.forecast_run_id);
      setScenarioRunId(stored.scenario_run_id ?? "");
      setScorAssessmentId(stored.scor_assessment_id ?? "");
      setPortfolioRunId(stored.portfolio_run_id ?? "");
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

  return (
    <div className="workspace dc-workspace">
      <header className="workspace-header dc-header">
        <div><span className="eyebrow">{copy.header.eyebrow}</span><h1>{copy.header.title}</h1><p>{copy.header.subtitle}</p></div>
        <div className="dc-boundary"><ShieldCheck size={18} /><span>{copy.header.boundary}<strong>{copy.header.noExecution}</strong></span></div>
      </header>
      <section className="dc-panel">
        <div className="dc-heading"><div><span>{copy.setup.index}</span><h2>{copy.setup.title}</h2></div><small>{preflight?.selection.dataset_name ?? "—"}</small></div>
        <div className="dc-setup-grid">
          <label><span>{copy.setup.forecast}</span><select value={forecastRunId} disabled={analyzing} onChange={(event) => { setForecastRunId(event.target.value); setScenarioRunId(""); setScorAssessmentId(""); selectPortfolio(""); }}>{forecasts.map((item) => <option key={item.id} value={item.id}>{item.data_cutoff} · {translateFrequency(item.frequency)} · {item.champion_model}</option>)}</select></label>
          <label><span>{copy.setup.scenario}</span><select value={scenarioRunId} disabled={analyzing || !preflight} onChange={(event) => { setScenarioRunId(event.target.value); setRun(null); setSelected(null); }}><option value="">{copy.setup.noScenario}</option>{preflight?.scenarios.map((item) => <option key={item.id} value={item.id}>{item.name} · {percent(item.relative_delta)}</option>)}</select></label>
          <label><span>{copy.setup.scor}</span><select value={scorAssessmentId} disabled={analyzing || !preflight} onChange={(event) => { setScorAssessmentId(event.target.value); setRun(null); setSelected(null); }}><option value="">{copy.setup.noScor}</option>{(preflight?.scor_assessments ?? []).map((item) => <option key={item.id} value={item.id}>{item.name} · {rate(item.data_coverage)}</option>)}</select></label>
          <label><span>{copy.setup.portfolio}</span><select value={portfolioRunId} disabled={analyzing || !preflight} onChange={(event) => selectPortfolio(event.target.value)}><option value="">{copy.setup.noPortfolio}</option>{preflight?.portfolios.map((item) => <option key={item.id} value={item.id}>{portfolioOptionLabel(item)}</option>)}</select></label>
          <label><span>{copy.setup.cutoff}</span><input type="datetime-local" value={cutoff} disabled={analyzing} onChange={(event) => setCutoff(event.target.value)} /></label>
        </div>
        {preflight && <div className="dc-source-strip"><div><span>{copy.setup.champion}</span><strong>{preflight.champion.model_name}</strong></div><div><span>{copy.setup.trajectory}</span><strong>{percent(preflight.forecast_summary.trajectory_delta)}</strong></div><div><span>{copy.setup.context}</span><strong>{preflight.relevant_context.length}</strong></div><div><span>{copy.setup.impacts}</span><strong>{preflight.usable_impacts.length}</strong></div><div><span>{copy.setup.scorAvailable}</span><strong>{preflight.scor_assessments?.length ?? 0}</strong></div><div><span>{copy.setup.portfoliosAvailable}</span><strong>{preflight.portfolios.length}</strong></div><div><span>{copy.setup.missing}</span><strong>{preflight.missing_operational_inputs.length}</strong></div></div>}
        {selectedScor && <div className="dc-scor-summary"><div><span>{copy.setup.scorSelected}</span><strong>{selectedScor.assessment_name}</strong><small>{dateOnly(selectedScor.period_start)} — {dateOnly(selectedScor.period_end)} · {selectedScor.benchmark_profile_name ?? copy.setup.noBenchmark}</small></div><div><span>{copy.setup.coverage}</span><strong>{rate(selectedScor.summary.data_coverage)}</strong><small>{selectedScor.summary.metrics_complete ?? 0} {copy.setup.complete} · {selectedScor.summary.metrics_insufficient ?? 0} {copy.setup.insufficient}</small></div><div><span>{scorTies.length ? copy.setup.criticalTie : copy.setup.criticalProcess}</span><strong>{scorCriticality}</strong><small>{copy.setup.nonCausal}</small></div></div>}
        {selectedPortfolio && portfolioItem && <div className="dc-portfolio-summary"><div><span>{copy.setup.portfolioSelected}</span><strong>{String(portfolioItem.product ?? copy.setup.aggregateSeries)} · {String(portfolioItem.location ?? copy.setup.allLocations)}</strong><small>Portfolio Run {selectedPortfolio.portfolio_run_id.slice(0, 8)} · {copy.setup.frozenSnapshot}</small></div><div><span>{copy.setup.portfolioRank}</span><strong>#{String(portfolioItem.rank ?? "—")}</strong><small>{copy.setup.priorityScore}: {Number(portfolioItem.priority_score ?? 0).toFixed(1)} / 100</small></div><div><span>{copy.setup.portfolioRisk}</span><strong>{ui.portfolio.risks[String(portfolioItem.risk_level) as keyof typeof ui.portfolio.risks] ?? String(portfolioItem.risk_level ?? "—")}</strong><small>{copy.setup.coverage}: {portfolioItem.inventory_coverage == null ? copy.setup.notCalculable : Number(portfolioItem.inventory_coverage).toFixed(2)}</small></div></div>}
        {portfolioHandoffNotice && <div className="dc-handoff-notice" role="status">{portfolioHandoffNotice}</div>}
        {scenarioRunId && <p className="dc-scenario-boundary">{copy.setup.scenarioBoundary}</p>}
        {error && <div className="ds-error-message">{error}</div>}
        <div className="dc-run"><button type="button" disabled={analyzing || !preflight} onClick={() => void analyze()}>{analyzing ? <RefreshCw size={16} /> : <Play size={16} />}{analyzing ? copy.setup.analyzing : copy.setup.analyze}</button><small>Forecast: {activeForecast?.id} · corte auditable {cutoff}</small></div>
      </section>
      {run && <><section className="dc-kpis"><article><span>{copy.kpis.open}</span><strong>{openCount}</strong></article><article><span>{copy.kpis.high}</span><strong>{run.summary.high_priority_count}</strong></article><article><span>{copy.kpis.review}</span><strong>{run.summary.requires_review_count}</strong></article><article><span>{copy.kpis.scenarios}</span><strong>{run.summary.scenario_considered ? 1 : 0}</strong></article><article><span>{copy.kpis.scor}</span><strong>{run.summary.scor_assessments_considered}</strong></article><article><span>{copy.kpis.portfolio}</span><strong>{run.summary.portfolios_considered}</strong></article></section><DecisionList recommendations={run.recommendations} selectedId={selected?.id ?? null} onSelect={setSelected} /><DecisionDetail decisionRun={run} recommendation={selected} saving={saving} onStatus={(status) => void updateStatus(status)} /><DecisionComparison run={run} /></>}
      <section className="dc-panel"><div className="dc-heading"><div><span>{copy.history.index}</span><h2>{copy.history.title}</h2></div><History size={17} /></div>{!runs.length ? <p className="dc-muted">{copy.history.empty}</p> : <div className="dc-history">{runs.map((item) => <button type="button" key={item.id} disabled={analyzing} onClick={() => void openStored(item)}><span><strong>{item.created_at.slice(0, 10)} · {item.recommendation_count} recomendaciones</strong><small>{item.forecast_run_id}{item.scenario_run_id ? " · con escenario" : " · baseline oficial"}{item.scor_assessment_id ? " · con SCOR" : ""}{item.portfolio_run_id ? " · con Portafolio" : ""}</small></span><b>{item.high_priority_count} alta/crítica</b></button>)}</div>}</section>
    </div>
  );
}
