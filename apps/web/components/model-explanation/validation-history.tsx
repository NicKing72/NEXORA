import type { ExplanationRun } from "@/lib/explanation-types";
import { interpolate, ui } from "@/lib/i18n";

function percent(value: unknown) {
  return typeof value === "number" ? `${(value * 100).toFixed(2)}%` : "—";
}

export function ValidationHistory({ run }: Readonly<{ run: ExplanationRun }>) {
  const copy = ui.modelExplanation.validation;
  const validation = run.source_snapshot.backtesting;
  return (
    <section className="mx-panel mx-validation">
      <div className="mx-section-heading"><div><span>{copy.index}</span><h2>{copy.title}</h2></div><div className="mx-validation-summary"><span>{copy.mean}<strong>{percent(validation.summary.mean_wmape)}</strong></span><span>{copy.dispersion}<strong>{percent(validation.summary.wmape_dispersion)}</strong></span></div></div>
      {validation.folds.length === 0 ? <p>{copy.empty}</p> : <div className="mx-folds">{validation.folds.map((fold) => <article key={fold.fold_index}><strong>{interpolate(copy.fold, { index: fold.fold_index })}</strong><dl><div><dt>{copy.training}</dt><dd>{fold.train_start} — {fold.train_end}</dd></div><div><dt>{copy.validation}</dt><dd>{fold.validation_start} — {fold.validation_end}</dd></div></dl><small>{interpolate(copy.observations, { train: fold.training_observations, validation: fold.validation_observations })}</small><div className="mx-fold-metrics"><span>WMAPE <b>{percent(fold.metrics.wmape)}</b></span><span>MAE <b>{fold.metrics.mae?.toFixed(2) ?? "—"}</b></span><span>RMSE <b>{fold.metrics.rmse?.toFixed(2) ?? "—"}</b></span></div></article>)}</div>}
    </section>
  );
}
