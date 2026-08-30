"use client";

import { Plus, Trash2 } from "lucide-react";

import { ui } from "@/lib/i18n";
import type {
  AssumptionKind,
  ContextImpactOption,
  ScenarioAssumptionDraft,
} from "@/lib/scenario-types";

const kinds = Object.keys(ui.scenarioLab.builder.types) as AssumptionKind[];

type Props = {
  assumptions: ScenarioAssumptionDraft[];
  evidence: ContextImpactOption[];
  disabled: boolean;
  onChange: (items: ScenarioAssumptionDraft[]) => void;
};

function unitLabel(kind: AssumptionKind) {
  if (kind === "demand_absolute") return ui.scenarioLab.builder.absolute;
  if (kind === "stock_restriction") return ui.scenarioLab.builder.capacity;
  return ui.scenarioLab.builder.percent;
}

export function AssumptionBuilder({ assumptions, evidence, disabled, onChange }: Readonly<Props>) {
  const copy = ui.scenarioLab.builder;
  function patch(id: string, values: Partial<ScenarioAssumptionDraft>) {
    onChange(assumptions.map((item) => (item.clientId === id ? { ...item, ...values } : item)));
  }
  function add() {
    const first = assumptions[0];
    onChange([
      ...assumptions,
      {
        clientId: `assumption-${assumptions.length + 1}-${performance.now().toFixed(0)}`,
        assumption_type: "demand_percent",
        label: "Nuevo supuesto",
        start_at: first?.start_at ?? "",
        end_at: first?.end_at ?? "",
        magnitude: 0.05,
      },
    ]);
  }
  return (
    <section className="sx-panel">
      <div className="sx-heading">
        <div><span>{copy.index}</span><h2>{copy.title}</h2></div>
        <button type="button" className="sx-secondary" disabled={disabled} onClick={add}>
          <Plus size={15} />{copy.add}
        </button>
      </div>
      <div className="sx-assumptions">
        {assumptions.map((item, index) => {
          const contextual = item.assumption_type === "context_impact";
          const displayedMagnitude = item.assumption_type === "demand_absolute"
            ? item.magnitude
            : item.magnitude * 100;
          return (
            <article key={item.clientId} className="sx-assumption">
              <div className="sx-assumption-top">
                <strong>{String(index + 1).padStart(2, "0")}</strong>
                <span className={contextual ? "is-evidence" : ""}>
                  {contextual ? copy.evidenceBadge : copy.manualBadge}
                </span>
                {assumptions.length > 1 && (
                  <button type="button" disabled={disabled} onClick={() => onChange(assumptions.filter((current) => current.clientId !== item.clientId))}>
                    <Trash2 size={14} />{copy.remove}
                  </button>
                )}
              </div>
              <div className="sx-assumption-grid">
                <label><span>{copy.type}</span><select value={item.assumption_type} disabled={disabled} onChange={(event) => {
                  const kind = event.target.value as AssumptionKind;
                  patch(item.clientId, { assumption_type: kind, magnitude: kind === "stock_restriction" ? 0.8 : kind === "demand_absolute" ? 5 : 0.05 });
                }}>{kinds.map((kind) => <option key={kind} value={kind}>{copy.types[kind]}</option>)}</select></label>
                {contextual ? (
                  <label className="sx-wide"><span>{copy.evidence}</span><select value={item.context_impact_estimate_id ?? ""} disabled={disabled} onChange={(event) => {
                    const selected = evidence.find((entry) => entry.estimate_id === event.target.value);
                    if (selected) patch(item.clientId, { label: selected.title, magnitude: selected.relative_delta, context_signal_id: selected.signal_id, context_impact_estimate_id: selected.estimate_id });
                  }}><option value="">Seleccionar evidencia…</option>{evidence.map((entry) => <option key={entry.estimate_id} value={entry.estimate_id}>{entry.title} · {(entry.relative_delta * 100).toFixed(1)}% · {entry.evidence_level}</option>)}</select></label>
                ) : (
                  <label className="sx-wide"><span>{copy.label}</span><input value={item.label} maxLength={160} disabled={disabled} onChange={(event) => patch(item.clientId, { label: event.target.value })} /></label>
                )}
                <label><span>{copy.start}</span><input type="date" value={item.start_at} disabled={disabled} onChange={(event) => patch(item.clientId, { start_at: event.target.value })} /></label>
                <label><span>{copy.end}</span><input type="date" value={item.end_at} disabled={disabled} onChange={(event) => patch(item.clientId, { end_at: event.target.value })} /></label>
                <label><span>{unitLabel(item.assumption_type)}</span><input type="number" step={item.assumption_type === "demand_absolute" ? "1" : "0.1"} value={Number.isFinite(displayedMagnitude) ? displayedMagnitude : 0} disabled={disabled || contextual} onChange={(event) => patch(item.clientId, { magnitude: item.assumption_type === "demand_absolute" ? Number(event.target.value) : Number(event.target.value) / 100 })} /></label>
              </div>
              {item.assumption_type === "stock_restriction" && <p className="sx-inline-warning">{ui.scenarioLab.warnings.supply}</p>}
              {contextual && <p className="sx-inline-warning">{ui.scenarioLab.warnings.causal}</p>}
            </article>
          );
        })}
      </div>
    </section>
  );
}
