import type { DecisionRecommendation } from "@/lib/decision-types";
import { ui } from "@/lib/i18n";

type Props = {
  recommendations: DecisionRecommendation[];
  selectedId: string | null;
  onSelect: (item: DecisionRecommendation) => void;
};

export function DecisionList({ recommendations, selectedId, onSelect }: Readonly<Props>) {
  const copy = ui.decisionCenter.queue;
  return (
    <section className="dc-panel dc-queue">
      <div className="dc-heading">
        <div><span>{copy.index}</span><h2>{copy.title}</h2></div>
        <strong>{recommendations.length}</strong>
      </div>
      <div className="dc-table-wrap">
        <table>
          <thead><tr><th>#</th><th>{copy.priority}</th><th>{copy.scope}</th><th>{copy.recommendation}</th><th>{copy.reason}</th><th>{copy.support}</th><th>{copy.status}</th></tr></thead>
          <tbody>
            {recommendations.map((item) => (
              <tr
                key={item.id}
                className={selectedId === item.id ? "is-selected" : ""}
                onClick={() => onSelect(item)}
              >
                <td>{String(item.rank).padStart(2, "0")}</td>
                <td><span className={`dc-priority dc-priority--${item.priority}`}>{ui.decisionCenter.priorities[item.priority]}</span></td>
                <td><strong>{item.product ?? "Todos"}</strong><small>{item.location ?? "Todas las ubicaciones"}</small></td>
                <td><strong>{item.title}</strong><small>{copy.supportAction}</small>{item.scor_origin && <span className={`dc-scor-badge dc-scor-badge--${item.scor_origin}`}>{ui.decisionCenter.scorOrigins[item.scor_origin]}</span>}{item.portfolio_origin && <span className={`dc-portfolio-badge dc-portfolio-badge--${item.portfolio_origin}`}>{ui.decisionCenter.portfolioOrigins[item.portfolio_origin]}</span>}</td>
                <td>{item.summary}</td>
                <td><b>{Math.round(item.support_score * 100)}%</b><small>{ui.decisionCenter.evidenceLevels[item.evidence_level as keyof typeof ui.decisionCenter.evidenceLevels] ?? item.evidence_level}</small></td>
                <td><span className={`dc-status dc-status--${item.status}`}>{ui.decisionCenter.statuses[item.status]}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
