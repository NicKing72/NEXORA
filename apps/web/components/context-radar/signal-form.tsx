import { Plus, X } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

import type { KnowledgeType, ManualSignalInput, ScopeType, SignalFamily } from "@/lib/context-types";
import { ui } from "@/lib/i18n";
import type { SeriesDimensions } from "@/lib/series-types";

const families = Object.keys(ui.contextRadar.families) as SignalFamily[];
const knowledgeTypes = Object.keys(ui.contextRadar.knowledgeTypes) as KnowledgeType[];
const scopes: ScopeType[] = ["global", "product", "category", "location", "custom"];

type Props = { datasetId: string; dimensions: SeriesDimensions; saving: boolean; onClose: () => void; onSave: (payload: ManualSignalInput) => Promise<void> };

function toIso(value: string): string {
  return new Date(value).toISOString();
}

export function SignalForm({ datasetId, dimensions, saving, onClose, onSave }: Readonly<Props>) {
  const copy = ui.contextRadar.form;
  const nowLocal = useMemo(() => {
    const date = new Date();
    date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
    return date.toISOString().slice(0, 16);
  }, []);
  const [family, setFamily] = useState<SignalFamily>("commercial");
  const [signalType, setSignalType] = useState("own_promotion");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [eventStart, setEventStart] = useState(nowLocal);
  const [eventEnd, setEventEnd] = useState("");
  const [availableAt, setAvailableAt] = useState(nowLocal);
  const [knowledgeType, setKnowledgeType] = useState<KnowledgeType>("observed");
  const [scopeType, setScopeType] = useState<ScopeType>("global");
  const [product, setProduct] = useState("");
  const [category, setCategory] = useState("");
  const [location, setLocation] = useState("");
  const [confidence, setConfidence] = useState("");
  const [sourceNote, setSourceNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (eventEnd && new Date(eventEnd) < new Date(eventStart)) { setError("La fecha final no puede ser anterior al inicio."); return; }
    const requiredScopeValue = scopeType === "product" ? product : scopeType === "category" ? category : scopeType === "location" ? location : "valid";
    if (!requiredScopeValue) { setError("Selecciona el valor correspondiente al alcance principal."); return; }
    setError(null);
    await onSave({
      dataset_id: datasetId, signal_family: family, signal_type: signalType, title, description,
      event_start: toIso(eventStart), event_end: eventEnd ? toIso(eventEnd) : null,
      observed_at: knowledgeType === "observed" ? toIso(availableAt) : null,
      available_at: toIso(availableAt), knowledge_type: knowledgeType, scope_type: scopeType,
      product: product || null, category: category || null, location: location || null,
      confidence: confidence ? Number(confidence) / 100 : null,
      source_reference: sourceNote || null, metadata: {},
    });
  }

  return <div className="cx-modal" role="dialog" aria-modal="true" aria-labelledby="cx-form-title"><form className="cx-form" onSubmit={(event) => void submit(event)}><div className="cx-form-header"><div><span className="section-index">{copy.index}</span><h2 id="cx-form-title">{copy.title}</h2><p>{copy.subtitle}</p></div><button type="button" aria-label={ui.contextRadar.actions.close} onClick={onClose}><X size={18} /></button></div><div className="cx-form-grid">
    <label><span>{copy.family}</span><select value={family} onChange={(event) => setFamily(event.target.value as SignalFamily)}>{families.map((item) => <option key={item} value={item}>{ui.contextRadar.families[item]}</option>)}</select></label>
    <label><span>{copy.type}</span><input required pattern="[a-z][a-z0-9_]+" maxLength={80} placeholder={copy.typeHint} value={signalType} onChange={(event) => setSignalType(event.target.value)} /></label>
    <label className="cx-span-2"><span>{copy.signalTitle}</span><input required minLength={2} maxLength={160} value={title} onChange={(event) => setTitle(event.target.value)} /></label>
    <label className="cx-span-2"><span>{copy.description}</span><textarea maxLength={2000} rows={3} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
    <label><span>{copy.start}</span><input required type="datetime-local" value={eventStart} onChange={(event) => setEventStart(event.target.value)} /></label>
    <label><span>{copy.end}</span><input type="datetime-local" value={eventEnd} onChange={(event) => setEventEnd(event.target.value)} /></label>
    <label><span>{copy.available}</span><input required type="datetime-local" value={availableAt} onChange={(event) => setAvailableAt(event.target.value)} /></label>
    <label><span>{copy.knowledge}</span><select value={knowledgeType} onChange={(event) => setKnowledgeType(event.target.value as KnowledgeType)}>{knowledgeTypes.map((item) => <option key={item} value={item}>{ui.contextRadar.knowledgeTypes[item]}</option>)}</select></label>
    <label><span>{copy.scope}</span><select value={scopeType} onChange={(event) => setScopeType(event.target.value as ScopeType)}>{scopes.map((item) => <option key={item} value={item}>{ui.contextRadar.scopes[item]}</option>)}</select></label>
    <label><span>{copy.confidence}</span><input type="number" min="0" max="100" step="1" value={confidence} onChange={(event) => setConfidence(event.target.value)} /></label>
    <label><span>{copy.product}</span><select value={product} onChange={(event) => setProduct(event.target.value)}><option value="">—</option>{dimensions.products.map((item) => <option key={item.value}>{item.value}</option>)}</select></label>
    <label><span>{copy.category}</span><select value={category} onChange={(event) => setCategory(event.target.value)}><option value="">—</option>{dimensions.categories.map((item) => <option key={item.value}>{item.value}</option>)}</select></label>
    <label><span>{copy.location}</span><select value={location} onChange={(event) => setLocation(event.target.value)}><option value="">—</option>{dimensions.locations.map((item) => <option key={item.value}>{item.value}</option>)}</select></label>
    <label><span>{copy.sourceNote}</span><input maxLength={1000} value={sourceNote} onChange={(event) => setSourceNote(event.target.value)} /></label>
  </div>{error && <p className="ds-error-message">{error}</p>}<div className="cx-form-footer"><small>{copy.confirmed}</small><button type="button" onClick={onClose}>{ui.contextRadar.actions.cancel}</button><button type="submit" disabled={saving}><Plus size={15} />{saving ? ui.contextRadar.actions.saving : ui.contextRadar.actions.save}</button></div></form></div>;
}
