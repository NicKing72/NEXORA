import type { SeriesStatistics as Statistics } from "@/lib/series-types";
import { interpolate, ui } from "@/lib/i18n";
import { formatMetric, formatSeriesDate } from "@/lib/series-formatters";

type Metric = {
  label: string;
  value: string;
  detail?: string;
};

function MetricGrid({ metrics }: Readonly<{ metrics: Metric[] }>) {
  return (
    <div className="dx-stat-grid">
      {metrics.map((metric) => (
        <div key={metric.label}>
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
          {metric.detail && <small>{metric.detail}</small>}
        </div>
      ))}
    </div>
  );
}

export function SeriesStatistics({ statistics }: Readonly<{ statistics: Statistics }>) {
  const copy = ui.demandExplorer.statistics;
  const series = statistics.series;
  const quality = statistics.underlying_quality;
  const seriesMetrics: Metric[] = [
    { label: copy.periods, value: formatMetric(series.periods, 0) },
    { label: copy.completePeriods, value: formatMetric(series.complete_periods, 0) },
    { label: copy.partialPeriods, value: formatMetric(series.partial_periods, 0) },
    { label: copy.analyzedPeriods, value: formatMetric(series.analyzed_periods, 0) },
    { label: copy.firstDate, value: formatSeriesDate(series.first_date) },
    { label: copy.lastDate, value: formatSeriesDate(series.last_date) },
    { label: copy.total, value: formatMetric(series.total_demand) },
    { label: copy.mean, value: formatMetric(series.mean_demand) },
    { label: copy.median, value: formatMetric(series.median_demand) },
    { label: copy.minimum, value: formatMetric(series.minimum_demand) },
    { label: copy.maximum, value: formatMetric(series.maximum_demand) },
    { label: copy.deviation, value: formatMetric(series.standard_deviation) },
    {
      label: copy.variation,
      value: series.coefficient_of_variation === null
        ? copy.unavailable
        : formatMetric(series.coefficient_of_variation, 3),
    },
    { label: copy.missingPeriods, value: formatMetric(series.completely_missing_periods, 0) },
    { label: copy.zeroPeriods, value: formatMetric(series.zero_demand_periods, 0) },
  ];
  const affected = quality.affected_periods;
  const qualityMetrics: Metric[] = [
    { label: copy.sourceObservations, value: formatMetric(quality.source_observations, 0) },
    {
      label: copy.sourceMissing,
      value: formatMetric(quality.missing_demand_values, 0),
      detail: interpolate(copy.affectedPeriods, { count: affected.missing }),
    },
    {
      label: copy.sourceZeros,
      value: formatMetric(quality.zero_demand_observations, 0),
      detail: interpolate(copy.affectedPeriods, { count: affected.zero }),
    },
    {
      label: copy.sourceOutliers,
      value: formatMetric(quality.outlier_observations, 0),
      detail: interpolate(copy.affectedPeriods, { count: affected.outlier }),
    },
    {
      label: copy.sourceStockouts,
      value: formatMetric(quality.possible_stockout_observations, 0),
      detail: interpolate(copy.affectedPeriods, { count: affected.stockout }),
    },
  ];
  return (
    <section className="dx-statistics" aria-labelledby="dx-statistics-title">
      <div className="dx-section-heading">
        <div>
          <span className="section-index">{copy.index}</span>
          <h2 id="dx-statistics-title">{copy.title}</h2>
        </div>
      </div>
      <div className="dx-stat-section">
        <div className="dx-stat-subheading">
          <h3>{copy.seriesTitle}</h3>
          <p>{copy.seriesDescription}</p>
        </div>
        <MetricGrid metrics={seriesMetrics} />
        <p className="dx-stat-note">{copy.analysisNote}</p>
      </div>
      <div className="dx-stat-section">
        <div className="dx-stat-subheading">
          <h3>{copy.qualityTitle}</h3>
          <p>{copy.qualityDescription}</p>
        </div>
        <MetricGrid metrics={qualityMetrics} />
      </div>
    </section>
  );
}
