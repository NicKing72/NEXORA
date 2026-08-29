import { Award } from "lucide-react";

import type { ForecastModelResult, ForecastRun } from "@/lib/forecast-types";
import { ui } from "@/lib/i18n";
import { formatMetric, formatSignedPercent } from "@/lib/series-formatters";

export function ChampionCard({ run, champion }: Readonly<{ run: ForecastRun; champion: ForecastModelResult }>) {
  const copy = ui.forecastLab.champion;
  const names = ui.forecastLab.modelNames;
  return <section className="fx-champion"><div className="fx-champion-title"><Award size={22} /><div><span>{copy.index}</span><h2>{names[champion.model_name as keyof typeof names] ?? champion.model_name}</h2></div></div><div className="fx-champion-metrics"><div><span>{copy.wmape}</span><strong>{champion.metrics.wmape === null || champion.metrics.wmape === undefined ? "—" : `${formatMetric(champion.metrics.wmape * 100)}%`}</strong></div><div><span>{copy.bias}</span><strong>{formatSignedPercent(champion.metrics.bias_percent === null || champion.metrics.bias_percent === undefined ? null : champion.metrics.bias_percent * 100)}</strong></div><div><span>{copy.stability}</span><strong>{ui.forecastLab.stability[champion.stability.label ?? "insufficient"]}</strong></div><div><span>{copy.folds}</span><strong>{champion.folds.length}</strong></div></div><p>{copy.reasons[run.champion_reason as keyof typeof copy.reasons] ?? run.champion_reason}</p></section>;
}
