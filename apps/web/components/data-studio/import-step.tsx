import { Database, FileSpreadsheet, LoaderCircle, UploadCloud } from "lucide-react";
import { useRef } from "react";

import type { Dataset, OperationState } from "@/lib/data-studio-types";
import { ui } from "@/lib/i18n";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toLocaleString("es-PE", { maximumFractionDigits: 1 })} KB`;
  return `${(bytes / (1024 * 1024)).toLocaleString("es-PE", { maximumFractionDigits: 1 })} MB`;
}

type ImportStepProps = {
  state: OperationState;
  dataset: Dataset | null;
  selectedSheet: string;
  error: string | null;
  onFile: (file: File) => void;
  onDemo: () => void;
  onSheetChange: (sheet: string) => void;
  onSheetConfirm: () => void;
  onDragState: (dragging: boolean) => void;
};

export function ImportStep({
  state,
  dataset,
  selectedSheet,
  error,
  onFile,
  onDemo,
  onSheetChange,
  onSheetConfirm,
  onDragState,
}: Readonly<ImportStepProps>) {
  const inputRef = useRef<HTMLInputElement>(null);
  const busy = state === "uploading" || state === "processing";

  return (
    <section className="ds-import-layout" aria-labelledby="import-heading">
      <div
        className={`ds-dropzone${state === "dragging" ? " is-dragging" : ""}`}
        onDragEnter={(event) => { event.preventDefault(); onDragState(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => { event.preventDefault(); onDragState(false); }}
        onDrop={(event) => {
          event.preventDefault();
          onDragState(false);
          const file = event.dataTransfer.files[0];
          if (file) onFile(file);
        }}
      >
        <input
          ref={inputRef}
          className="ds-file-input"
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onFile(file);
            event.target.value = "";
          }}
        />
        <span className="ds-upload-icon">
          {busy ? <LoaderCircle className="ds-spin" size={25} /> : <UploadCloud size={25} />}
        </span>
        <span className="section-index">{ui.dataStudio.import.index}</span>
        <h2 id="import-heading">{ui.dataStudio.import.title}</h2>
        <p>{ui.dataStudio.import.description}</p>
        <button className="ds-primary-action" type="button" disabled={busy} onClick={() => inputRef.current?.click()}>
          <FileSpreadsheet size={16} /> {ui.dataStudio.import.select}
        </button>
        <span className="ds-file-rules">{ui.dataStudio.import.rules}</span>
      </div>

      <aside className="ds-import-aside">
        <div>
          <span className="section-index">{ui.dataStudio.import.demoIndex}</span>
          <h3>{ui.dataStudio.import.demoTitle}</h3>
          <p>{ui.dataStudio.import.demoDescription}</p>
        </div>
        <button className="ds-secondary-action" type="button" disabled={busy} onClick={onDemo}>
          <Database size={16} /> {ui.dataStudio.import.useDemo}
        </button>
        <div className="ds-trust-note">
          <span>{ui.dataStudio.import.localProcessing}</span><span>{ui.dataStudio.import.seed}</span><span>{ui.dataStudio.import.noExternalApi}</span>
        </div>
      </aside>

      {error && <div className="ds-inline-message ds-inline-message--error" role="alert">{error}</div>}

      {dataset && (
        <div className="ds-file-receipt">
          <div><span className="section-index">{ui.dataStudio.import.registered}</span><strong>{dataset.original_filename}</strong></div>
          <dl>
            <div><dt>{ui.dataStudio.import.size}</dt><dd>{formatBytes(dataset.file_size)}</dd></div>
            <div><dt>{ui.dataStudio.import.rows}</dt><dd>{dataset.row_count?.toLocaleString("es-PE") ?? ui.dataStudio.import.pending}</dd></div>
            <div><dt>{ui.dataStudio.import.columns}</dt><dd>{dataset.column_count ?? ui.dataStudio.import.pending}</dd></div>
            <div><dt>ID</dt><dd>{dataset.id.slice(0, 8)}</dd></div>
          </dl>
          {dataset.status === "awaiting_sheet" && (
            <div className="ds-sheet-picker">
              <label htmlFor="sheet-selection">{ui.dataStudio.import.chooseSheet}</label>
              <select id="sheet-selection" value={selectedSheet} onChange={(event) => onSheetChange(event.target.value)}>
                {dataset.available_sheets.map((sheet) => <option key={sheet}>{sheet}</option>)}
              </select>
              <button className="ds-primary-action" type="button" onClick={onSheetConfirm}>{ui.dataStudio.import.inspectSheet}</button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
