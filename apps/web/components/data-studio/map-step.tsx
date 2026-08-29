import { ArrowLeft, ArrowRight, Asterisk, CheckCircle2, SlidersHorizontal } from "lucide-react";

import { PreviewTable } from "@/components/data-studio/preview-table";
import type { ColumnMapping, Dataset, DatasetPreview, OperationState } from "@/lib/data-studio-types";
import { interpolate, ui } from "@/lib/i18n";

const roleGroups = [
  {
    label: ui.dataStudio.map.required,
    roles: [
      { id: "date", ...ui.dataStudio.map.roles.date },
      { id: "demand", ...ui.dataStudio.map.roles.demand },
    ],
  },
  {
    label: ui.dataStudio.map.recommended,
    roles: [{ id: "product", ...ui.dataStudio.map.roles.product }],
  },
  {
    label: ui.dataStudio.map.optional,
    roles: [
      { id: "price", ...ui.dataStudio.map.roles.price },
      { id: "stock", ...ui.dataStudio.map.roles.stock },
      { id: "promotion", ...ui.dataStudio.map.roles.promotion },
      { id: "location", ...ui.dataStudio.map.roles.location },
      { id: "category", ...ui.dataStudio.map.roles.category },
      { id: "cost", ...ui.dataStudio.map.roles.cost },
      { id: "lead_time", ...ui.dataStudio.map.roles.lead_time },
      { id: "channel", ...ui.dataStudio.map.roles.channel },
      { id: "supplier", ...ui.dataStudio.map.roles.supplier },
    ],
  },
] as const;

const canonicalRoles = new Set(roleGroups.flatMap((group) => group.roles.map((role) => role.id)));

type MapStepProps = {
  dataset: Dataset;
  preview: DatasetPreview;
  mappings: ColumnMapping[];
  state: OperationState;
  error: string | null;
  onAssign: (role: string, column: string) => void;
  onClassifyUnassigned: (column: string, role: "external" | "ignore") => void;
  onBack: () => void;
  onContinue: () => void;
};

export function MapStep({ dataset, preview, mappings, state, error, onAssign, onClassifyUnassigned, onBack, onContinue }: Readonly<MapStepProps>) {
  const byRole = new Map(mappings.map((mapping) => [mapping.role, mapping]));
  const assignedColumns = new Set(
    mappings.filter((mapping) => canonicalRoles.has(mapping.role as never)).map((mapping) => mapping.column_name),
  );
  const requiredReady = byRole.has("date") && byRole.has("demand");
  const busy = state === "processing";

  return (
    <div className="ds-map-layout">
      <section className="ds-map-panel" aria-labelledby="mapping-heading">
        <div className="ds-section-heading">
          <div><span className="section-index">{ui.dataStudio.map.index}</span><h2 id="mapping-heading">{ui.dataStudio.map.title}</h2></div>
          <SlidersHorizontal size={20} />
        </div>
        <div className="ds-source-strip">
          <span><strong>{dataset.original_filename}</strong><small>{dataset.row_count?.toLocaleString("es-PE")} {ui.dataStudio.map.rows} · {dataset.column_count} {ui.dataStudio.map.columns}</small></span>
          <span className="ds-id-chip">{dataset.id.slice(0, 8)}</span>
        </div>

        <div className="ds-role-groups">
          {roleGroups.map((group) => (
            <div className="ds-role-group" key={group.label}>
              <span className="ds-role-group-label">{group.label}</span>
              {group.roles.map((role) => {
                const mapping = byRole.get(role.id);
                return (
                  <div className={`ds-role-row${role.id === "date" || role.id === "demand" ? " is-required" : ""}`} key={role.id}>
                    <span className="ds-role-copy">
                      <strong>{role.label}{(role.id === "date" || role.id === "demand") && <Asterisk size={9} />}</strong>
                      <small>{role.description}</small>
                    </span>
                    <select aria-label={`${ui.dataStudio.map.columnAssignedTo} ${role.label}`} value={mapping?.column_name ?? ""} onChange={(event) => onAssign(role.id, event.target.value)}>
                      <option value="">{ui.dataStudio.map.notFound}</option>
                      {dataset.columns.map((column) => (
                        <option disabled={assignedColumns.has(column.name) && mapping?.column_name !== column.name} key={column.name} value={column.name}>{column.name}</option>
                      ))}
                    </select>
                    <span className={`ds-confidence${mapping ? " is-found" : ""}`}>
                      {mapping ? mapping.source === "manual" ? ui.dataStudio.map.manual : `${Math.round(mapping.confidence * 100)}%` : "—"}
                    </span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        <div className="ds-unassigned-section">
          <span className="ds-role-group-label">{ui.dataStudio.map.remaining}</span>
          <div className="ds-unassigned-grid">
            {mappings.filter((mapping) => !canonicalRoles.has(mapping.role as never)).map((mapping) => (
              <div key={mapping.column_name}>
                <span><strong>{mapping.column_name}</strong><small>{dataset.columns.find((column) => column.name === mapping.column_name)?.data_type}</small></span>
                <select value={mapping.role === "external" ? "external" : "ignore"} onChange={(event) => onClassifyUnassigned(mapping.column_name, event.target.value as "external" | "ignore")}>
                  <option value="ignore">{ui.dataStudio.map.ignore}</option>
                  <option value="external">{ui.dataStudio.map.external}</option>
                </select>
              </div>
            ))}
          </div>
        </div>

        {error && <div className="ds-inline-message ds-inline-message--error" role="alert">{error}</div>}
        <div className="ds-flow-actions">
          <button className="ds-ghost-action" type="button" onClick={onBack}><ArrowLeft size={15} /> {ui.dataStudio.map.importAnother}</button>
          <span className={`ds-required-state${requiredReady ? " is-ready" : ""}`}>
            <CheckCircle2 size={15} /> {requiredReady ? ui.dataStudio.map.criticalReady : ui.dataStudio.map.criticalRequired}
          </span>
          <button className="ds-primary-action" type="button" disabled={!requiredReady || busy} onClick={onContinue}>
            {busy ? ui.dataStudio.map.validating : ui.dataStudio.map.saveValidate} <ArrowRight size={15} />
          </button>
        </div>
      </section>

      <section className="ds-preview-section" aria-labelledby="preview-heading">
        <div className="ds-section-heading ds-section-heading--compact">
          <div><span className="section-index">{ui.dataStudio.preview.index}</span><h2 id="preview-heading">{interpolate(ui.dataStudio.preview.firstObservations, { count: preview.rows.length })}</h2></div>
          <span className="ds-readonly-chip">{ui.dataStudio.preview.readOnly}</span>
        </div>
        <PreviewTable preview={preview} />
      </section>
    </div>
  );
}
