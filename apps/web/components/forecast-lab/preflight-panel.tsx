import { AlertTriangle, Check, Minus, RefreshCw } from "lucide-react";

import type { ForecastPreflight } from "@/lib/forecast-types";
import { interpolate, translateFrequency, ui } from "@/lib/i18n";
import { formatSeriesDate } from "@/lib/series-formatters";

type PreflightPanelProps = { preflight: ForecastPreflight | null; loading: boolean };

export function PreflightPanel({ preflight, loading }: Readonly<PreflightPanelProps>) {
  const copy = ui.forecastLab.preflight;
  if (loading || !preflight) {
    return <section className="fx-panel fx-preflight"><div className="fx-inline-loading"><RefreshCw size={16} />{copy.loading}</div></section>;
  }
  const preparation = preflight.preprocessing;
  const items = [
    { ok: true, text: interpolate(copy.observations, { count: preparation.valid_training_values }) },
    { ok: true, text: interpolate(copy.frequency, { frequency: translateFrequency(preflight.selection.resolved_frequency) }) },
    { ok: true, text: interpolate(copy.partials, { count: preparation.excluded_partial_periods }) },
    { ok: Boolean(preflight.seasonality.candidate_period), text: interpolate(copy.seasonality, { period: preflight.seasonality.candidate_period ?? "—" }) },
    { ok: preflight.seasonality.evidence === "high", text: interpolate(copy.seasonalEvidence, { evidence: ui.demandExplorer.seasonality.evidenceValues[preflight.seasonality.evidence as keyof typeof ui.demandExplorer.seasonality.evidenceValues] ?? preflight.seasonality.evidence ?? "—" }) },
    { ok: preflight.holt_winters.recommendation === "favorable", text: interpolate(copy.seasonalRecommendation, { recommendation: ui.demandExplorer.eligibility.recommendationValues[preflight.holt_winters.recommendation as keyof typeof ui.demandExplorer.eligibility.recommendationValues] ?? preflight.holt_winters.recommendation ?? "—" }) },
    { warning: preparation.outliers_preserved > 0, text: interpolate(copy.outliers, { count: preparation.outliers_preserved }) },
    { warning: preparation.possible_stockouts_preserved > 0, text: interpolate(copy.stockouts, { count: preparation.possible_stockouts_preserved }) },
    { ok: preparation.missing_before === preparation.interpolated_values, text: interpolate(copy.missing, { count: preparation.missing_before - preparation.interpolated_values }) },
    ...(preparation.interpolated_values ? [{ warning: true, text: interpolate(copy.interpolated, { count: preparation.interpolated_values }) }] : []),
    { ok: preparation.continuous_for_training, text: preparation.continuous_for_training ? copy.continuous : copy.discontinuous },
  ];
  const additive = preflight.model_eligibility.find((item) => item.model_name === "holt_winters_additive");
  const multiplicative = preflight.model_eligibility.find((item) => item.model_name === "holt_winters_multiplicative");
  const availability = (model: typeof additive, name: string) => {
    if (!model) return null;
    const reasonCode = model.backtest_reason ?? model.final_fit_reason;
    const reasonTemplate = reasonCode
      ? ui.forecastLab.reasons[reasonCode as keyof typeof ui.forecastLab.reasons]
      : null;
    const unit = copy.periodUnits[
      preflight.selection.resolved_frequency as keyof typeof copy.periodUnits
    ] ?? copy.periodUnits.periods;
    const reason = reasonTemplate
      ? interpolate(reasonTemplate, { period: preflight.seasonality.candidate_period ?? "—", unit })
      : reasonCode;
    return <article><strong>{name}</strong><dl><div><dt>{copy.finalFit}</dt><dd className={model.final_fit_eligible ? "is-ok" : "is-warning"}>{model.final_fit_eligible ? copy.technicallyEligible : copy.notEligible}</dd></div><div><dt>{copy.backtesting}</dt><dd className={model.backtest_evaluable ? "is-ok" : "is-warning"}>{model.backtest_evaluable ? interpolate(copy.evaluable, { count: model.evaluable_folds, total: model.total_folds }) : copy.notEvaluable}</dd></div></dl>{reason && <p><b>{copy.reason}:</b> {reason}</p>}</article>;
  };
  return (
    <section className="fx-panel fx-preflight" aria-labelledby="fx-preflight-title">
      <div className="fx-heading"><div><span className="section-index">{copy.index}</span><h2 id="fx-preflight-title">{copy.title}</h2></div><div className="fx-cutoff"><span>{ui.forecastLab.header.cutoff}: {formatSeriesDate(preflight.data_cutoff)}</span><span>{ui.forecastLab.header.trainingCutoff}: {formatSeriesDate(preflight.training_cutoff)}</span></div></div>
      <div className="fx-check-grid">{items.map((item) => <div key={item.text} className={item.warning ? "is-warning" : item.ok ? "is-ok" : "is-muted"}>{item.warning ? <AlertTriangle size={15} /> : item.ok ? <Check size={15} /> : <Minus size={15} />}<span>{item.text}</span></div>)}</div>
      <div className="fx-model-eligibility">{availability(additive, copy.additive)}{availability(multiplicative, copy.multiplicative)}</div>
    </section>
  );
}
