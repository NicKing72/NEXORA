import { FlaskConical, ScanSearch, ShieldCheck } from "lucide-react";

import { ui } from "@/lib/i18n";
import type { ReportRequest, ReportType, SourceSummary } from "@/lib/report-types";

type Props = {
  request: ReportRequest;
  options: Record<string, SourceSummary[]>;
  loading: boolean;
  validating: boolean;
  generating: boolean;
  canGenerate: boolean;
  onChange: (key: keyof ReportRequest, value: string | null) => void;
  onValidate: () => void;
  onGenerate: () => void;
  onDemo: () => void;
};

function optionLabel(item: SourceSummary) {
  const name = item.name ?? item.title ?? item.champion_model ?? item.id.slice(0, 8);
  const detail = item.frequency ? ` · ${item.frequency}` : "";
  return `${name}${detail} · ${item.id.slice(0, 8)}`;
}

function SourceSelect({
  label,
  value,
  items,
  disabled,
  onChange,
}: Readonly<{
  label: string;
  value: string | null;
  items: SourceSummary[];
  disabled: boolean;
  onChange: (value: string | null) => void;
}>) {
  return (
    <label>
      <span>{label}</span>
      <select value={value ?? ""} disabled={disabled} onChange={(event) => onChange(event.target.value || null)}>
        <option value="">{ui.reports.builder.none}</option>
        {items.map((item) => <option key={item.id} value={item.id}>{optionLabel(item)}</option>)}
      </select>
    </label>
  );
}

export function ReportBuilder(props: Readonly<Props>) {
  const copy = ui.reports.builder;
  const busy = props.loading || props.validating || props.generating;
  return (
    <section className="rp-panel rp-builder">
      <div className="rp-section-heading">
        <div><span>{copy.index}</span><h2>{copy.title}</h2></div>
        <button type="button" className="rp-demo-action" disabled={busy} onClick={props.onDemo}>
          <FlaskConical size={16} />{copy.demo}
        </button>
      </div>
      {props.loading ? <p className="rp-loading">{copy.loading}</p> : <>
        <div className="rp-builder-grid">
          <label><span>{copy.reportType}</span><select value={props.request.report_type} disabled={busy} onChange={(event) => props.onChange("report_type", event.target.value as ReportType)}>{Object.entries(ui.reports.types).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <label className="rp-title-field"><span>{copy.reportTitle}</span><input value={props.request.title} maxLength={180} disabled={busy} onChange={(event) => props.onChange("title", event.target.value)} /></label>
          <label><span>{copy.cutoff}</span><input type="datetime-local" value={props.request.report_cutoff} disabled={busy} onChange={(event) => props.onChange("report_cutoff", event.target.value)} /></label>
          <SourceSelect label={copy.forecast} value={props.request.forecast_run_id} items={props.options.forecasts ?? []} disabled={busy} onChange={(value) => props.onChange("forecast_run_id", value)} />
          <SourceSelect label={copy.scenario} value={props.request.scenario_run_id} items={props.options.scenarios ?? []} disabled={busy} onChange={(value) => props.onChange("scenario_run_id", value)} />
          <SourceSelect label={copy.scor} value={props.request.scor_assessment_id} items={props.options.scor ?? []} disabled={busy} onChange={(value) => props.onChange("scor_assessment_id", value)} />
          <SourceSelect label={copy.portfolio} value={props.request.portfolio_run_id} items={props.options.portfolios ?? []} disabled={busy} onChange={(value) => props.onChange("portfolio_run_id", value)} />
          <SourceSelect label={copy.decision} value={props.request.decision_run_id} items={props.options.decisions ?? []} disabled={busy} onChange={(value) => props.onChange("decision_run_id", value)} />
          <SourceSelect label={copy.explanation} value={props.request.explanation_run_id} items={props.options.explanations ?? []} disabled={busy} onChange={(value) => props.onChange("explanation_run_id", value)} />
        </div>
        <p className="rp-contract-note"><ShieldCheck size={15} />{copy.exactIds}</p>
        <div className="rp-builder-actions">
          <button type="button" className="rp-secondary-action" disabled={busy || !props.request.title.trim()} onClick={props.onValidate}><ScanSearch size={16} />{props.validating ? copy.validating : copy.validate}</button>
          <button type="button" className="rp-primary-action" disabled={busy || !props.canGenerate} onClick={props.onGenerate}><FileCheck2Icon />{props.generating ? copy.generating : copy.generate}</button>
        </div>
      </>}
    </section>
  );
}

function FileCheck2Icon() {
  return <span aria-hidden="true">→</span>;
}
