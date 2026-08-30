import type { ScorProcess, ScorProcessResult } from "@/lib/scor-types";
import { ui } from "@/lib/i18n";

const order: ScorProcess[] = ["PLAN", "SOURCE", "MAKE", "DELIVER", "RETURN"];

export function ScorProcessMap({ processes, selected, onSelect }: Readonly<{
  processes: ScorProcessResult[];
  selected: ScorProcess | "ALL";
  onSelect: (process: ScorProcess | "ALL") => void;
}>) {
  const byProcess = Object.fromEntries(processes.map((item) => [item.process, item]));
  return (
    <section className="sd-panel">
      <div className="sd-heading"><div><span>{ui.scorDiagnostic.map.index}</span><h2>{ui.scorDiagnostic.map.title}</h2></div><button type="button" onClick={() => onSelect("ALL")}>Ver todos</button></div>
      <div className="sd-process-map">
        {order.map((process, index) => {
          const item = byProcess[process];
          return <div className="sd-process-step" key={process}><button type="button" className={selected === process ? "is-active" : ""} onClick={() => onSelect(process)}><span>{String(index + 1).padStart(2, "0")}</span><strong>{ui.scorDiagnostic.process[process]}</strong><small>{item?.metrics_complete ?? 0}/{item?.metrics_total ?? 0} {ui.scorDiagnostic.map.complete}</small><small>{item?.metrics_insufficient ?? 0} {ui.scorDiagnostic.map.insufficient} · {item?.metrics_not_applicable ?? 0} {ui.scorDiagnostic.map.notApplicable}</small><b>{item?.weighted_gap_score == null ? "Sin benchmark" : `${item.weighted_gap_score.toFixed(1)} / 100`}</b></button>{index < order.length - 1 && <i>→</i>}</div>;
        })}
      </div>
    </section>
  );
}
