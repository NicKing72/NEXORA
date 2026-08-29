import type { DatasetPreview } from "@/lib/data-studio-types";
import { interpolate, ui } from "@/lib/i18n";

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? ui.dataStudio.preview.yes : ui.dataStudio.preview.no;
  return String(value);
}

export function PreviewTable({ preview }: Readonly<{ preview: DatasetPreview }>) {
  return (
    <div className="ds-preview-frame">
      <div className="ds-table-scroll">
        <table className="ds-preview-table">
          <thead>
            <tr>
              <th className="ds-row-number">#</th>
              {preview.columns.map((column) => <th key={column}>{column}</th>)}
            </tr>
          </thead>
          <tbody>
            {preview.rows.map((row, index) => (
              <tr key={index}>
                <td className="ds-row-number">{String(index + 1).padStart(2, "0")}</td>
                {preview.columns.map((column) => (
                  <td className={row[column] === null ? "is-null" : ""} key={column}>
                    {displayValue(row[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="ds-preview-footer">
        <span>{interpolate(ui.dataStudio.preview.showing, { shown: preview.rows.length, total: preview.total_rows.toLocaleString("es-PE") })}</span>
        <span>{ui.dataStudio.preview.sourceValues}</span>
      </div>
    </div>
  );
}
