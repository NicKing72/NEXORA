import type { ForecastModelResult } from "@/lib/forecast-types";
import { interpolate, ui } from "@/lib/i18n";
import { formatMetric, formatSeriesDate } from "@/lib/series-formatters";

export function BacktestingView({ model }: Readonly<{ model: ForecastModelResult }>) {
  const copy = ui.forecastLab.backtesting;
  return <section className="fx-panel fx-folds"><div className="fx-heading"><div><span className="section-index">{copy.index}</span><h2>{copy.title}</h2></div></div>{model.folds.length === 0 ? <p className="fx-muted">{copy.noFolds}</p> : <div className="fx-fold-list">{model.folds.map((fold) => <article key={fold.id}><div><strong>{interpolate(copy.fold, { index: fold.fold_index })}</strong><small>{interpolate(copy.observations, { train: fold.training_observations, validation: fold.validation_observations })}</small></div><dl><div><dt>{copy.train}</dt><dd>{formatSeriesDate(fold.train_start)} → {formatSeriesDate(fold.train_end)}</dd></div><div><dt>{copy.validation}</dt><dd>{formatSeriesDate(fold.validation_start)} → {formatSeriesDate(fold.validation_end)}</dd></div></dl><span>WMAPE <b>{fold.metrics.wmape === null || fold.metrics.wmape === undefined ? "—" : `${formatMetric(fold.metrics.wmape * 100)}%`}</b></span></article>)}</div>}</section>;
}
