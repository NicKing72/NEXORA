"use client";

import { X } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

import type { ScorDefinition, ScorMetricInputDraft, ScorProcess } from "@/lib/scor-types";
import { ui } from "@/lib/i18n";

type Props = {
  definitions: ScorDefinition[];
  saving: boolean;
  onClose: () => void;
  onCreate: (input: {
    name: string;
    companyName: string;
    periodStart: string;
    periodEnd: string;
    cutoff: string;
    sourceName: string;
    metricInputs: ScorMetricInputDraft[];
  }) => void;
};

const processes: ScorProcess[] = ["PLAN", "SOURCE", "MAKE", "DELIVER", "RETURN"];

export function ScorAssessmentForm({ definitions, saving, onClose, onCreate }: Readonly<Props>) {
  const copy = ui.scorDiagnostic.form;
  const [process, setProcess] = useState<ScorProcess>("PLAN");
  const [name, setName] = useState("Diagnóstico semestral");
  const [companyName, setCompanyName] = useState("");
  const [periodStart, setPeriodStart] = useState("2026-01-01");
  const [periodEnd, setPeriodEnd] = useState("2026-06-30");
  const [cutoff, setCutoff] = useState("2026-07-01T12:00");
  const [sourceName, setSourceName] = useState("Acumulados empresariales declarados");
  const [values, setValues] = useState<Record<string, Record<string, string>>>({});
  const [notApplicable, setNotApplicable] = useState<Record<string, boolean>>({});
  const [metadata, setMetadata] = useState<Record<string, Record<string, string>>>({
    M02: { time_unit: "minutos" }, D06: { time_unit: "horas" },
  });
  const visible = useMemo(
    () => definitions.filter((item) => item.process === process),
    [definitions, process],
  );

  function updateValue(metricId: string, inputId: string, value: string) {
    setValues((current) => ({
      ...current,
      [metricId]: { ...(current[metricId] ?? {}), [inputId]: value },
    }));
  }

  function updateMetadata(metricId: string, key: string, value: string) {
    setMetadata((current) => ({
      ...current,
      [metricId]: { ...(current[metricId] ?? {}), [key]: value },
    }));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const metricInputs = definitions.flatMap((definition) => {
      const raw = values[definition.id] ?? {};
      const parsed = Object.fromEntries(
        Object.entries(raw)
          .filter(([, value]) => value !== "")
          .map(([key, value]) => [key, Number(value)]),
      );
      if (!Object.keys(parsed).length && !notApplicable[definition.id]) return [];
      return [{
        metric_id: definition.id,
        values: parsed,
        metadata: metadata[definition.id] ?? {},
        not_applicable: Boolean(notApplicable[definition.id]),
        available_at: cutoff,
      } satisfies ScorMetricInputDraft];
    });
    onCreate({ name, companyName, periodStart, periodEnd, cutoff, sourceName, metricInputs });
  }

  return (
    <div className="sd-modal-backdrop" role="presentation">
      <form className="sd-modal" onSubmit={submit}>
        <header><div><span>INPUTS BASE</span><h2>{copy.title}</h2><p>{copy.description}</p></div><button type="button" onClick={onClose} aria-label={copy.close}><X size={18} /></button></header>
        <div className="sd-form-meta">
          <label><span>{copy.name}</span><input required value={name} onChange={(event) => setName(event.target.value)} /></label>
          <label><span>{copy.company}</span><input value={companyName} onChange={(event) => setCompanyName(event.target.value)} /></label>
          <label><span>{copy.start}</span><input required type="date" value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} /></label>
          <label><span>{copy.end}</span><input required type="date" value={periodEnd} onChange={(event) => setPeriodEnd(event.target.value)} /></label>
          <label><span>{copy.cutoff}</span><input required type="datetime-local" value={cutoff} onChange={(event) => setCutoff(event.target.value)} /></label>
          <label><span>{copy.source}</span><input required value={sourceName} onChange={(event) => setSourceName(event.target.value)} /></label>
        </div>
        <nav className="sd-form-processes" aria-label={copy.process}>
          {processes.map((item) => <button type="button" className={item === process ? "is-active" : ""} key={item} onClick={() => setProcess(item)}>{item}</button>)}
        </nav>
        <div className="sd-input-metrics">
          {visible.map((definition) => (
            <article key={definition.id}>
              <div className="sd-input-heading"><span>{definition.id}</span><strong>{definition.display_name}</strong><label><input type="checkbox" checked={Boolean(notApplicable[definition.id])} onChange={(event) => setNotApplicable((current) => ({ ...current, [definition.id]: event.target.checked }))} />{copy.notApplicable}</label></div>
              <p>{definition.formula}</p>
              {!definition.inputs.length && <small>Se calcula a partir de KPI dependientes completos.</small>}
              <div className="sd-raw-grid">
                {definition.inputs.map((input) => <label key={input.id}><span>{input.label}</span><input type="number" step="any" min={input.nonnegative ? 0 : undefined} disabled={Boolean(notApplicable[definition.id])} value={values[definition.id]?.[input.id] ?? ""} onChange={(event) => updateValue(definition.id, input.id, event.target.value)} /></label>)}
                {["M02", "D06"].includes(definition.id) && <label><span>{copy.timeUnit}</span><select value={metadata[definition.id]?.time_unit ?? "horas"} onChange={(event) => updateMetadata(definition.id, "time_unit", event.target.value)}><option value="minutos">Minutos</option><option value="horas">Horas</option><option value="días">Días</option></select></label>}
                {["D08", "R04"].includes(definition.id) && <label><span>{copy.currency}</span><input placeholder="PEN, USD…" value={metadata[definition.id]?.currency ?? ""} onChange={(event) => updateMetadata(definition.id, "currency", event.target.value.toUpperCase())} /></label>}
              </div>
            </article>
          ))}
        </div>
        <footer><button type="button" onClick={onClose}>{copy.close}</button><button className="sd-primary" type="submit" disabled={saving}>{copy.create}</button></footer>
      </form>
    </div>
  );
}
