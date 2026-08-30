import { AlertTriangle, FileSearch, Fingerprint, ShieldCheck } from "lucide-react";

import type { DecisionRecommendation, DecisionStatus } from "@/lib/decision-types";
import { ui } from "@/lib/i18n";

type Props = {
  recommendation: DecisionRecommendation | null;
  saving: boolean;
  onStatus: (status: DecisionStatus) => void;
};

const allowedTransitions: Record<DecisionStatus, DecisionStatus[]> = {
  open: ["acknowledged", "under_review", "dismissed", "resolved"],
  acknowledged: ["under_review", "dismissed", "resolved"],
  under_review: ["acknowledged", "dismissed", "resolved"],
  dismissed: ["under_review"],
  resolved: ["under_review"],
};

export function DecisionDetail({ recommendation, saving, onStatus }: Readonly<Props>) {
  const copy = ui.decisionCenter.detail;
  if (!recommendation) {
    return (
      <section className="dc-panel dc-detail dc-detail--empty">
        <div className="dc-heading"><div><span>{copy.index}</span><h2>{copy.detected}</h2></div></div>
        <p>{ui.decisionCenter.queue.select}</p>
      </section>
    );
  }
  return (
    <section className="dc-panel dc-detail">
      <div className="dc-heading">
        <div><span>{copy.index}</span><h2>{recommendation.title}</h2></div>
        <span className={`dc-priority dc-priority--${recommendation.priority}`}>{ui.decisionCenter.priorities[recommendation.priority]}</span>
      </div>
      <div className="dc-detail-grid">
        <article><small>{copy.detected}</small><p>{recommendation.summary}</p></article>
        <article><small>{copy.why}</small><p>{recommendation.rationale}</p></article>
        <article><small>{copy.review}</small><p>{recommendation.title}. {copy.noOrder}</p></article>
        <article><small>{copy.unknown}</small>{recommendation.limitations.length ? <ul>{recommendation.limitations.map((item) => <li key={item}>{item}</li>)}</ul> : <p>{copy.noLimitations}</p>}</article>
      </div>
      <div className="dc-evidence">
        <div className="dc-subheading"><FileSearch size={16} /><strong>{copy.evidence}</strong></div>
        {recommendation.evidence.map((item) => (
          <details key={item.id}>
            <summary>{item.description}</summary>
            <p>{copy.evidenceType}: {ui.decisionCenter.evidenceTypes[item.evidence_type as keyof typeof ui.decisionCenter.evidenceTypes] ?? item.evidence_type} · {copy.source}: {item.source_id ?? copy.analysisSnapshot}</p>
            <pre>{JSON.stringify(item.snapshot, null, 2)}</pre>
          </details>
        ))}
      </div>
      <div className="dc-provenance">
        <Fingerprint size={17} />
        <span><strong>{copy.provenance}</strong><p>Forecast: {recommendation.forecast_run_id}{recommendation.scenario_run_id ? ` · Escenario: ${recommendation.scenario_run_id}` : ""}</p><small>{copy.noCausality}</small></span>
      </div>
      <div className="dc-boundaries"><ShieldCheck size={16} />{copy.noOrder}{recommendation.scenario_run_id && <><AlertTriangle size={16} />{ui.decisionCenter.setup.scenarioBoundary}</>}</div>
      <label className="dc-lifecycle">
        <span>{copy.lifecycle}</span>
        <select value={recommendation.status} disabled={saving} onChange={(event) => onStatus(event.target.value as DecisionStatus)}>
          {[recommendation.status, ...allowedTransitions[recommendation.status]].map((value) => <option key={value} value={value}>{ui.decisionCenter.statuses[value]}</option>)}
        </select>
      </label>
    </section>
  );
}
