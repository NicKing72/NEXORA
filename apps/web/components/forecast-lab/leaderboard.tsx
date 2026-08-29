import type { ForecastModelResult } from "@/lib/forecast-types";
import { interpolate, ui } from "@/lib/i18n";
import { formatMetric, formatSignedPercent } from "@/lib/series-formatters";

type LeaderboardProps = { models: ForecastModelResult[]; frequency: string; selectedId: number | null; onSelect: (model: ForecastModelResult) => void };

function percentage(value: number | null | undefined): string {
  return value === null || value === undefined ? ui.forecastLab.leaderboard.notApplicable : `${formatMetric(value * 100)}%`;
}

export function Leaderboard({ models, frequency, selectedId, onSelect }: Readonly<LeaderboardProps>) {
  const copy = ui.forecastLab.leaderboard;
  const names = ui.forecastLab.modelNames;
  const statuses = ui.forecastLab.status;
  const stability = ui.forecastLab.stability;
  return (
    <section className="fx-panel fx-leaderboard" aria-labelledby="fx-leaderboard-title">
      <div className="fx-heading"><div><span className="section-index">{copy.index}</span><h2 id="fx-leaderboard-title">{copy.title}</h2></div></div>
      <div className="fx-table-wrap"><table><thead><tr><th>#</th><th>{copy.model}</th><th>{copy.wmape}</th><th>{copy.mae}</th><th>{copy.rmse}</th><th>{copy.smape}</th><th>{copy.mape}</th><th>{copy.bias}</th><th>{copy.stability}</th><th>{copy.status}</th></tr></thead><tbody>{models.map((model) => {
        const status = statuses[model.status];
        const modelName = names[model.model_name as keyof typeof names] ?? model.model_name;
        const reasonTemplate = model.failure_reason ? ui.forecastLab.reasons[model.failure_reason as keyof typeof ui.forecastLab.reasons] : null;
        const periodValue = model.parameters.seasonal_period;
        const period = typeof periodValue === "string" || typeof periodValue === "number" ? periodValue : "—";
        const unit = ui.forecastLab.preflight.periodUnits[
          frequency as keyof typeof ui.forecastLab.preflight.periodUnits
        ] ?? ui.forecastLab.preflight.periodUnits.periods;
        const reason = reasonTemplate ? interpolate(reasonTemplate, { period, unit }) : model.failure_reason;
        return <tr key={model.id} className={`${model.rank === 1 ? "is-champion" : ""} ${selectedId === model.id ? "is-selected" : ""}`} onClick={() => onSelect(model)}><td>{model.rank ?? "—"}</td><td><strong>{modelName}</strong>{model.rank === 1 && <small>{copy.champion}</small>}{reason && <em>{reason}</em>}</td><td>{percentage(model.metrics.wmape)}</td><td>{formatMetric(model.metrics.mae ?? null)}</td><td>{formatMetric(model.metrics.rmse ?? null)}</td><td>{percentage(model.metrics.smape)}</td><td>{percentage(model.metrics.mape)}</td><td>{formatSignedPercent(model.metrics.bias_percent === null || model.metrics.bias_percent === undefined ? null : model.metrics.bias_percent * 100)}</td><td>{stability[model.stability.label ?? "insufficient"]}</td><td><span className={`fx-status fx-status--${model.status}`}>{status}</span></td></tr>;
      })}</tbody></table></div>
    </section>
  );
}
