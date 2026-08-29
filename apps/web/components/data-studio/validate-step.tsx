import { AlertCircle, ArrowLeft, ArrowRight, CheckCircle2, Info, RefreshCcw, ShieldAlert } from "lucide-react";
import type { CSSProperties } from "react";

import type { OperationState, QualityAssessment } from "@/lib/data-studio-types";
import { translateFrequency, translateQualityIssue, translateQualityIssueLabel, ui } from "@/lib/i18n";

const severityIcons = { ERROR: ShieldAlert, WARNING: AlertCircle, INFO: Info } as const;

type ValidateStepProps = {
  assessment: QualityAssessment;
  state: OperationState;
  error: string | null;
  onBack: () => void;
  onRerun: () => void;
  onReady: () => void;
};

export function ValidateStep({ assessment, state, error, onBack, onRerun, onReady }: Readonly<ValidateStepProps>) {
  const { report, issues } = assessment;
  const busy = state === "processing";
  const scoreStyle = { "--readiness": `${report.readiness_score * 3.6}deg` } as CSSProperties;

  return (
    <div className="ds-validation-layout">
      <section className="ds-readiness-panel">
        <div className="ds-section-heading">
          <div><span className="section-index">{ui.dataStudio.validate.index}</span><h2>{ui.dataStudio.validate.title}</h2></div>
          <button className="ds-icon-action" type="button" aria-label={ui.dataStudio.validate.rerun} disabled={busy} onClick={onRerun}><RefreshCcw size={16} /></button>
        </div>
        <div className="ds-score-block">
          <div className="ds-score-ring" style={scoreStyle}><span><strong>{report.readiness_score}</strong><small>/ 100</small></span></div>
          <div>
            <strong>{report.has_critical_errors ? ui.dataStudio.validate.actionRequired : report.readiness_score >= 80 ? ui.dataStudio.validate.forecastReady : ui.dataStudio.validate.usableReview}</strong>
            <p>{ui.dataStudio.validate.scoreDescription}</p>
          </div>
        </div>
        <div className="ds-component-list">
          {Object.entries(report.component_scores).map(([key, score]) => (
            <div key={key}>
              <span><strong>{ui.dataStudio.validate.components[key as keyof typeof ui.dataStudio.validate.components] ?? key}</strong><small>{score}</small></span>
              <i><b style={{ width: `${score}%` }} /></i>
            </div>
          ))}
        </div>
        <div className="ds-deductions">
          <span className="ds-role-group-label">{ui.dataStudio.validate.whyLost}</span>
          {report.deductions.length ? report.deductions.map((item) => (
            <div key={item.component}><span>{ui.dataStudio.validate.components[item.component as keyof typeof ui.dataStudio.validate.components] ?? item.component}</span><strong>−{item.points_lost}</strong></div>
          )) : <p>{ui.dataStudio.validate.noDeductions}</p>}
        </div>
      </section>

      <section className="ds-quality-panel">
        <div className="ds-section-heading">
          <div><span className="section-index">{ui.dataStudio.validate.ledger}</span><h2>{ui.dataStudio.validate.findings}</h2></div>
          <div className="ds-severity-summary">
            {(["ERROR", "WARNING", "INFO"] as const).map((severity) => <span className={`is-${severity.toLowerCase()}`} key={severity}>{issues.filter((issue) => issue.severity === severity).length} {ui.dataStudio.validate.severities[severity]}</span>)}
          </div>
        </div>
        <div className="ds-quality-facts">
          <div><span>{ui.dataStudio.validate.frequency}</span><strong>{translateFrequency(report.frequency)}</strong><small>{Math.round(report.frequency_confidence * 100)}% {ui.dataStudio.validate.confidence}</small></div>
          <div><span>{ui.dataStudio.validate.period}</span><strong>{report.duration_days ?? 0} {ui.dataStudio.validate.days}</strong><small>{report.observations.toLocaleString("es-PE")} {ui.dataStudio.validate.observations}</small></div>
          <div><span>{ui.dataStudio.validate.products}</span><strong>{report.sku_count}</strong><small>{report.location_count} {ui.dataStudio.validate.locations}</small></div>
          <div><span>{ui.dataStudio.validate.mapped}</span><strong>{report.mapped_variable_count}</strong><small>{ui.dataStudio.validate.canonicalVariables}</small></div>
        </div>
        <div className="ds-issue-list">
          {issues.map((issue) => {
            const Icon = severityIcons[issue.severity];
            return (
              <article className={`ds-issue is-${issue.severity.toLowerCase()}`} key={issue.id}>
                <span className="ds-issue-icon"><Icon size={16} /></span>
                <span><strong>{translateQualityIssue(issue.code, issue.count)}</strong><small>{translateQualityIssueLabel(issue.code)}{issue.column_name ? ` · ${issue.column_name}` : ""}</small></span>
                <span className="ds-issue-count">{issue.count}</span>
              </article>
            );
          })}
          {!issues.length && <div className="ds-empty-quality"><CheckCircle2 size={18} /> {ui.dataStudio.validate.noIssues}</div>}
        </div>
      </section>

      {error && <div className="ds-inline-message ds-inline-message--error" role="alert">{error}</div>}
      <div className="ds-flow-actions ds-flow-actions--full">
        <button className="ds-ghost-action" type="button" onClick={onBack}><ArrowLeft size={15} /> {ui.dataStudio.validate.reviewMapping}</button>
        <span className="ds-validation-note">{ui.dataStudio.validate.warningNote}</span>
        <button className="ds-primary-action" type="button" disabled={report.has_critical_errors || busy} onClick={onReady}>
          {busy ? ui.dataStudio.validate.preparing : ui.dataStudio.validate.markReady} <ArrowRight size={15} />
        </button>
      </div>
    </div>
  );
}
