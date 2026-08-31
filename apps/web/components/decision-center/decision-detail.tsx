import { AlertTriangle, Boxes, FileSearch, Fingerprint, ShieldCheck } from "lucide-react";
import Link from "next/link";

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
  const scorEvidence = recommendation.evidence.find((item) => item.evidence_type.startsWith("scor_"));
  const scorSnapshot = scorEvidence?.snapshot ?? null;
  const scorAssessment = scorSnapshot && typeof scorSnapshot.assessment === "object" && scorSnapshot.assessment !== null
    ? scorSnapshot.assessment as Record<string, unknown>
    : null;
  const scorMetric = scorSnapshot && typeof scorSnapshot.metric === "object" && scorSnapshot.metric !== null
    ? scorSnapshot.metric as Record<string, unknown>
    : null;
  const scorTarget = scorMetric && typeof scorMetric.target === "object" && scorMetric.target !== null
    ? scorMetric.target as Record<string, unknown>
    : null;
  const portfolioEvidence = recommendation.evidence.find((item) => item.evidence_type.startsWith("portfolio_"));
  const portfolioSnapshot = portfolioEvidence?.snapshot ?? null;
  const portfolioRun = portfolioSnapshot && typeof portfolioSnapshot.portfolio === "object" && portfolioSnapshot.portfolio !== null
    ? portfolioSnapshot.portfolio as Record<string, unknown>
    : null;
  const portfolioItem = portfolioSnapshot && typeof portfolioSnapshot.item === "object" && portfolioSnapshot.item !== null
    ? portfolioSnapshot.item as Record<string, unknown>
    : null;
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
      {scorEvidence && scorAssessment && scorMetric && <div className="dc-scor-evidence">
        <div className="dc-subheading"><ShieldCheck size={16} /><strong>{copy.scorEvidence}</strong><span>{recommendation.scor_origin ? ui.decisionCenter.scorOrigins[recommendation.scor_origin] : "SCOR"}</span></div>
        <div className="dc-scor-evidence-grid">
          <div><small>{copy.scorAssessment}</small><strong>{String(scorAssessment.assessment_name ?? "—")}</strong><span>{String(scorAssessment.period_start ?? "—").slice(0, 10)} — {String(scorAssessment.period_end ?? "—").slice(0, 10)}</span></div>
          <div><small>{copy.scorMetric}</small><strong>{String(scorMetric.metric_id ?? "—")} · {String(scorMetric.metric_name ?? "—")}</strong><span>{String(scorMetric.process ?? "—")} · {String(scorMetric.evidence_status ?? "—")}</span></div>
          <div><small>{copy.scorResult}</small><strong>{scorMetric.raw_result == null ? "—" : `${Number(scorMetric.raw_result).toFixed(2)} ${String(scorMetric.unit ?? "")}`}</strong><span>{copy.scorTarget}: {scorTarget?.target == null ? "—" : String(scorTarget.target)} · Gap: {scorMetric.gap_score == null ? "—" : `${Number(scorMetric.gap_score).toFixed(1)} / 100`}</span></div>
          <div><small>{copy.scorCoverage}</small><strong>{`${(Number(scorMetric.process_coverage ?? 0) * 100).toFixed(1)}%`}</strong><span>{copy.scorVersion}: {String(scorMetric.calculation_version ?? "—")}</span></div>
        </div>
        <div className="dc-scor-evidence-footer"><span>{copy.scorSnapshot}</span>{recommendation.scor_assessment_id && <Link href={`/scor-diagnostic?assessment_id=${recommendation.scor_assessment_id}`}>{copy.openScor}</Link>}</div>
      </div>}
      {portfolioEvidence && portfolioRun && portfolioItem && <div className="dc-portfolio-evidence">
        <div className="dc-subheading"><Boxes size={16} /><strong>{copy.portfolioEvidence}</strong><span>{recommendation.portfolio_origin ? ui.decisionCenter.portfolioOrigins[recommendation.portfolio_origin] : "Portafolio"}</span></div>
        <div className="dc-portfolio-evidence-grid">
          <div><small>{copy.portfolioRun}</small><strong>{String(portfolioRun.portfolio_run_id ?? "—")}</strong><span>{copy.portfolioCutoff}: {String(portfolioRun.cutoff ?? "—").slice(0, 16)}</span></div>
          <div><small>{copy.portfolioSeries}</small><strong>#{String(portfolioItem.rank ?? "—")} · {String(portfolioItem.product ?? "Serie agregada")}</strong><span>{String(portfolioItem.location ?? "Todas las ubicaciones")}</span></div>
          <div><small>{copy.portfolioRisk}</small><strong>{ui.portfolio.risks[String(portfolioItem.risk_level) as keyof typeof ui.portfolio.risks] ?? String(portfolioItem.risk_level ?? "—")}</strong><span>{copy.portfolioScore}: {Number(portfolioItem.priority_score ?? 0).toFixed(1)} / 100</span></div>
          <div><small>{copy.portfolioCoverage}</small><strong>{portfolioItem.inventory_coverage == null ? copy.notCalculable : Number(portfolioItem.inventory_coverage).toFixed(2)}</strong><span>{copy.portfolioCompleteness}: {String(portfolioItem.operational_data_completeness ?? "—")}</span></div>
        </div>
        <div className="dc-scor-evidence-footer"><span>{copy.portfolioSnapshot}</span>{recommendation.portfolio_run_id && <Link href={`/portfolio?portfolio_run_id=${recommendation.portfolio_run_id}`}>{copy.openPortfolio}</Link>}</div>
      </div>}
      <div className="dc-provenance">
        <Fingerprint size={17} />
        <span><strong>{copy.provenance}</strong><p>Forecast: {recommendation.forecast_run_id}{recommendation.scenario_run_id ? ` · Escenario: ${recommendation.scenario_run_id}` : ""}{recommendation.portfolio_run_id ? ` · Portafolio: ${recommendation.portfolio_run_id}` : ""}</p><small>{copy.noCausality}</small></span>
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
