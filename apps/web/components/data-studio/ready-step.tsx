import { ArrowLeft, ArrowRight, CalendarRange, Check, Database, MapPin, PackageCheck } from "lucide-react";
import Link from "next/link";

import type { ReadyPayload } from "@/lib/data-studio-types";
import { canonicalRoleLabel, interpolate, translateFrequency, ui } from "@/lib/i18n";

export function ReadyStep({ payload, onReview }: Readonly<{ payload: ReadyPayload; onReview: () => void }>) {
  const { dataset, report, issues } = payload;
  const warnings = issues.filter((issue) => issue.severity === "WARNING");
  const mapping = dataset.mappings.filter((item) => item.role !== "ignore");
  const localTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const importedAt = new Intl.DateTimeFormat("es-PE", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(dataset.imported_at));
  return (
    <div className="ds-ready-layout">
      <section className="ds-ready-hero">
        <span className="ds-ready-mark"><Check size={28} /></span>
        <span className="section-index">{ui.dataStudio.ready.index}</span>
        <h2>{ui.dataStudio.ready.title}</h2>
        <p>{ui.dataStudio.ready.description}</p>
        <div className="ds-ready-metrics">
          <div><CalendarRange size={17} /><span><strong>{report.duration_days}</strong><small>{ui.dataStudio.ready.days}</small></span></div>
          <div><PackageCheck size={17} /><span><strong>{report.sku_count}</strong><small>SKU</small></span></div>
          <div><MapPin size={17} /><span><strong>{report.location_count}</strong><small>{ui.dataStudio.ready.locations}</small></span></div>
          <div><Database size={17} /><span><strong>{translateFrequency(report.frequency)}</strong><small>{ui.dataStudio.ready.frequency}</small></span></div>
          <div className="is-score"><span><strong>{report.readiness_score}</strong><small>{ui.dataStudio.ready.readiness}</small></span></div>
        </div>
      </section>

      <div className="ds-ready-details">
        <section>
          <div className="ds-section-heading ds-section-heading--compact"><div><span className="section-index">{ui.dataStudio.ready.columnContract}</span><h3>{interpolate(ui.dataStudio.ready.mappedVariables, { count: mapping.length })}</h3></div></div>
          <div className="ds-ready-mapping">
            {mapping.map((item) => <div key={item.column_name}><span>{canonicalRoleLabel(item.role)}</span><strong>{item.column_name}</strong><small>{ui.dataStudio.ready.sources[item.source as keyof typeof ui.dataStudio.ready.sources] ?? item.source}</small></div>)}
          </div>
        </section>
        <section>
          <div className="ds-section-heading ds-section-heading--compact"><div><span className="section-index">{ui.dataStudio.ready.persistentRecord}</span><h3>{ui.dataStudio.ready.sourceStatus}</h3></div></div>
          <dl className="ds-ready-source">
            <div><dt>{ui.dataStudio.ready.origin}</dt><dd>{dataset.source_type === "demo" ? ui.dataStudio.ready.syntheticDemo : dataset.original_filename}</dd></div>
            <div><dt>{ui.dataStudio.ready.imported}</dt><dd title={interpolate(ui.dataStudio.ready.localTimeZone, { zone: localTimeZone })}>{importedAt}</dd></div>
            <div><dt>{ui.dataStudio.ready.datasetId}</dt><dd>{dataset.id}</dd></div>
            <div><dt>{ui.dataStudio.ready.fileHash}</dt><dd>{dataset.sha256.slice(0, 20)}…</dd></div>
            <div><dt>{ui.dataStudio.ready.pendingWarnings}</dt><dd>{warnings.length}</dd></div>
          </dl>
        </section>
      </div>

      <div className="ds-flow-actions ds-flow-actions--full">
        <button className="ds-ghost-action" type="button" onClick={onReview}><ArrowLeft size={15} /> {ui.dataStudio.ready.reviewData}</button>
        <span className="ds-validation-note">{ui.dataStudio.ready.forecastBoundary}</span>
        <Link className="ds-primary-action" href="/demand-explorer">{ui.dataStudio.ready.openExplorer} <ArrowRight size={15} /></Link>
      </div>
    </div>
  );
}
