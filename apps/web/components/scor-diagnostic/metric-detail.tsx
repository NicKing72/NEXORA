import type { ScorAssessment, ScorDefinition, ScorMetricResult } from "@/lib/scor-types";
import { ui } from "@/lib/i18n";

function rawValue(metric: ScorMetricResult, inputId: string): unknown {
  const direct = metric.inputs[inputId];
  if (direct != null) return direct;
  const values = metric.inputs.values;
  return typeof values === "object" && values !== null ? (values as Record<string, unknown>)[inputId] : null;
}

function dateOnly(value: string) {
  return new Date(value).toLocaleDateString("es-PE", { timeZone: "UTC" });
}

export function ScorMetricDetail({ assessment, metric, definition }: Readonly<{
  assessment: ScorAssessment;
  metric: ScorMetricResult | null;
  definition: ScorDefinition | null;
}>) {
  if (!metric || !definition) return <section className="sd-panel sd-detail"><p>{ui.scorDiagnostic.matrix.select}</p></section>;
  const copy = ui.scorDiagnostic.detail;
  return (
    <section className="sd-panel sd-detail">
      <div className="sd-heading"><div><span>{metric.metric_id} / {metric.process}</span><h2>{metric.display_name}</h2></div><span className={`sd-evidence sd-evidence--${metric.evidence_status}`}>{ui.scorDiagnostic.evidence[metric.evidence_status]}</span></div>
      <div className="sd-detail-grid">
        <article><small>{copy.inputs}</small><dl>{definition.inputs.map((input) => <div key={input.id}><dt>{input.label}</dt><dd>{String(rawValue(metric, input.id) ?? "Ausente")}</dd></div>)}</dl></article>
        <article><small>{copy.substituted}</small><code>{metric.substituted_formula || copy.noResult}</code><p>{metric.reason ? ui.scorDiagnostic.errorReasons[metric.reason as keyof typeof ui.scorDiagnostic.errorReasons] ?? metric.reason : `${metric.result_value?.toFixed(4)} ${metric.unit}`}</p></article>
        <article><small>{copy.period}</small><p>{dateOnly(assessment.period_start)} — {dateOnly(assessment.period_end)}</p></article>
        <article><small>{copy.source}</small><p>{assessment.source_name}</p><small>{copy.version}: {metric.algorithm_version}</small></article>
      </div>
      {metric.gap_score != null && <div className="sd-gap-detail"><strong>NEXORA Gap Score: {metric.gap_score.toFixed(1)} / 100</strong><span>{String(metric.target.explanation ?? "Evaluado contra la meta configurada.")}</span></div>}
    </section>
  );
}
