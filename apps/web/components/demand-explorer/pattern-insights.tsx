import { Activity, CheckCircle2, CircleSlash2, Waves } from "lucide-react";

import type { SeriesProfile } from "@/lib/series-types";
import { interpolate, ui } from "@/lib/i18n";
import { formatMetric, formatSignedPercent } from "@/lib/series-formatters";

export function PatternInsights({ profile }: Readonly<{ profile: SeriesProfile }>) {
  const { pattern, seasonality, holt_winters: eligibility } = profile;
  const patternCopy = ui.demandExplorer.pattern;
  const seasonalityCopy = ui.demandExplorer.seasonality;
  const eligibilityCopy = ui.demandExplorer.eligibility;
  const seasonalityLabel = seasonality.candidate_label
    ? seasonalityCopy.labels[seasonality.candidate_label as keyof typeof seasonalityCopy.labels]
    : null;
  const seasonalityConclusion = seasonality.conclusion === "potential"
    ? seasonalityCopy.potential
    : seasonality.conclusion === "inconclusive"
      ? seasonalityCopy.inconclusive
      : seasonalityCopy.insufficient;
  const eligibilityReason = eligibility.candidate_period === null
    ? eligibilityCopy.unsupported
    : eligibility.compatible
      ? interpolate(eligibilityCopy.sufficient, {
          observations: eligibility.eligible_periods,
          cycles: eligibility.complete_cycles,
          period: eligibility.candidate_period,
        })
      : interpolate(eligibilityCopy.insufficient, {
          observations: eligibility.eligible_periods,
          required: eligibility.required_observations ?? 0,
          period: eligibility.candidate_period,
        });
  return (
    <div className="dx-insights-grid">
      <section className="dx-pattern-panel" aria-labelledby="dx-pattern-title">
        <div className="dx-section-heading">
          <div><span className="section-index">{patternCopy.index}</span><h2 id="dx-pattern-title">{patternCopy.title}</h2></div>
          <Activity size={18} />
        </div>
        <div className="dx-pattern-facts">
          <div>
            <span>{patternCopy.trend}</span>
            <strong>{patternCopy.trendValues[pattern.trend]}</strong>
            <small>{interpolate(patternCopy.approximateChange, { value: formatSignedPercent(pattern.approximate_change_percent) })}</small>
          </div>
          <div>
            <span>{patternCopy.volatility}</span>
            <strong>{patternCopy.volatilityValues[pattern.volatility]}</strong>
            <small>{patternCopy.coefficientAbbreviation} {formatMetric(profile.statistics.series.coefficient_of_variation, 3)}</small>
          </div>
          <div>
            <span>{patternCopy.intermittence}</span>
            <strong>{pattern.intermittent ? patternCopy.intermittent : patternCopy.continuous}</strong>
            <small>{interpolate(patternCopy.zeroPeriods, { value: formatMetric(pattern.zero_percentage) })}{pattern.adi === null ? "" : ` · ${interpolate(patternCopy.adi, { value: formatMetric(pattern.adi, 3) })}`}</small>
          </div>
        </div>
        <p className="dx-method-note">
          {interpolate(patternCopy.descriptiveOnly, {
            periods: pattern.analyzed_periods,
            excluded: pattern.excluded_partial_periods,
          })}
        </p>
      </section>

      <section className="dx-seasonality-panel" aria-labelledby="dx-seasonality-title">
        <div className="dx-section-heading">
          <div><span className="section-index">{seasonalityCopy.index}</span><h2 id="dx-seasonality-title">{seasonalityCopy.title}</h2></div>
          <Waves size={18} />
        </div>
        <strong className="dx-seasonality-candidate">
          {seasonalityLabel && seasonality.candidate_period
            ? interpolate(seasonalityCopy.candidate, { label: seasonalityLabel, period: seasonality.candidate_period })
            : seasonalityCopy.noCandidate}
        </strong>
        <p>{seasonalityConclusion}</p>
        <div className="dx-evidence-row">
          <span>{seasonalityCopy.evidence}</span>
          <strong>{seasonalityCopy.evidenceValues[seasonality.evidence]}</strong>
          <small>{seasonality.autocorrelation === null ? "—" : interpolate(seasonalityCopy.autocorrelation, { value: formatMetric(seasonality.autocorrelation, 3) })}</small>
        </div>
      </section>

      <section className={`dx-eligibility-panel${eligibility.compatible ? " is-compatible" : ""}`} aria-labelledby="dx-eligibility-title">
        <div className="dx-section-heading">
          <div><span className="section-index">{eligibilityCopy.index}</span><h2 id="dx-eligibility-title">{eligibilityCopy.title}</h2></div>
          {eligibility.compatible ? <CheckCircle2 size={18} /> : <CircleSlash2 size={18} />}
        </div>
        <div className="dx-compatible-state">
          <span>{eligibilityCopy.compatible}</span>
          <strong>{eligibility.compatible ? eligibilityCopy.yes : eligibilityCopy.no}</strong>
        </div>
        <p>{eligibilityReason}</p>
        <div className="dx-eligibility-facts">
          <div><span>{eligibilityCopy.candidatePeriod}</span><strong>{eligibility.candidate_period ?? "—"}</strong></div>
          <div><span>{eligibilityCopy.completeCycles}</span><strong>{eligibility.complete_cycles}</strong></div>
          <div><span>{eligibilityCopy.seasonalEvidence}</span><strong>{seasonalityCopy.evidenceValues[eligibility.seasonal_evidence]}</strong></div>
          <div><span>{eligibilityCopy.recommendation}</span><strong>{eligibilityCopy.recommendationValues[eligibility.recommendation]}</strong></div>
        </div>
        {eligibility.missing_values > 0 && <div className="dx-missing-warning">{interpolate(eligibilityCopy.missingWarning, { count: eligibility.missing_values })}</div>}
        <small>{eligibilityCopy.boundary}</small>
      </section>
    </div>
  );
}
