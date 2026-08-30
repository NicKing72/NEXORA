import { AlertTriangle, Fingerprint } from "lucide-react";

import { translateScenarioWarning, ui } from "@/lib/i18n";
import type { ScenarioRun } from "@/lib/scenario-types";

function number(value?: number | null) {
  return value == null ? "—" : new Intl.NumberFormat("es-PE", { maximumFractionDigits: 1 }).format(value);
}

export function ScenarioSummary({ scenario }: Readonly<{ scenario: ScenarioRun }>) {
  const copy = ui.scenarioLab.result;
  const metrics = [
    [copy.totalBaseline, number(scenario.summary.baseline_total)],
    [copy.totalScenario, number(scenario.summary.scenario_total)],
    [copy.delta, scenario.summary.relative_delta == null ? number(scenario.summary.absolute_delta) : `${scenario.summary.relative_delta >= 0 ? "+" : ""}${(scenario.summary.relative_delta * 100).toFixed(1)}%`],
    [copy.affected, number(scenario.summary.affected_periods)],
    [copy.maxChange, number(scenario.summary.max_period_change)],
  ];
  return <>
    <section className="sx-result-metrics">{metrics.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</section>
    <section className="sx-audit"><Fingerprint size={18} /><div><strong>{copy.provenance}</strong><p>Baseline: {scenario.forecast_run_id} · Champion: {scenario.champion_model} · combinación en orden declarado.</p><small>{copy.noOfficial}</small></div></section>
    {scenario.warnings.length > 0 && <section className="sx-warning-list"><AlertTriangle size={17} /><div>{scenario.warnings.map((warning) => <p key={warning}>{translateScenarioWarning(warning)}</p>)}</div></section>}
  </>;
}
