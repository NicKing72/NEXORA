import { ShieldCheck } from "lucide-react";

import type { ContextFilters, SignalFamily, SignalStatus, SourceType } from "@/lib/context-types";
import { interpolate, ui } from "@/lib/i18n";
import type { ReadyDatasetSummary, SeriesDimensions } from "@/lib/series-types";

const families = Object.keys(ui.contextRadar.families) as SignalFamily[];
const statuses = Object.keys(ui.contextRadar.statuses) as SignalStatus[];
const sources = Object.keys(ui.contextRadar.sources) as SourceType[];

type Props = {
  datasets: ReadyDatasetSummary[];
  dimensions: SeriesDimensions;
  filters: ContextFilters;
  onChange: (patch: Partial<ContextFilters>) => void;
};

export function ContextFiltersPanel({ datasets, dimensions, filters, onChange }: Readonly<Props>) {
  const copy = ui.contextRadar.filters;
  const cutoffLabel = filters.cutoff ? new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeStyle: "short" }).format(new Date(filters.cutoff)) : "—";
  return (
    <section className="cx-panel cx-filters" aria-labelledby="cx-filters-title">
      <div className="cx-heading"><div><span className="section-index">{copy.index}</span><h2 id="cx-filters-title">{copy.title}</h2></div><span className="cx-safety"><ShieldCheck size={14} />{copy.safety}</span></div>
      <div className="cx-filter-grid">
        <label><span>{copy.dataset}</span><select value={filters.datasetId} onChange={(event) => onChange({ datasetId: event.target.value })}>{datasets.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label><span>{copy.product}</span><select value={filters.product} onChange={(event) => onChange({ product: event.target.value })}><option value="">{copy.allProducts}</option>{dimensions.products.map((item) => <option key={item.value}>{item.value}</option>)}</select></label>
        <label><span>{copy.location}</span><select value={filters.location} onChange={(event) => onChange({ location: event.target.value })}><option value="">{copy.allLocations}</option>{dimensions.locations.map((item) => <option key={item.value}>{item.value}</option>)}</select></label>
        <label><span>{copy.category}</span><select value={filters.category} onChange={(event) => onChange({ category: event.target.value })}><option value="">{copy.allCategories}</option>{dimensions.categories.map((item) => <option key={item.value}>{item.value}</option>)}</select></label>
        <label><span>{copy.family}</span><select value={filters.family} onChange={(event) => onChange({ family: event.target.value })}><option value="">{copy.allFamilies}</option>{families.map((item) => <option key={item} value={item}>{ui.contextRadar.families[item]}</option>)}</select></label>
        <label><span>{copy.status}</span><select value={filters.status} onChange={(event) => onChange({ status: event.target.value })}><option value="">{copy.allStatuses}</option>{statuses.map((item) => <option key={item} value={item}>{ui.contextRadar.statuses[item]}</option>)}</select></label>
        <label><span>{copy.source}</span><select value={filters.source} onChange={(event) => onChange({ source: event.target.value })}><option value="">{copy.allSources}</option>{sources.map((item) => <option key={item} value={item}>{ui.contextRadar.sources[item]}</option>)}</select></label>
        <label><span>{copy.from}</span><input type="date" value={filters.eventFrom} onChange={(event) => onChange({ eventFrom: event.target.value })} /></label>
        <label><span>{copy.to}</span><input type="date" value={filters.eventTo} onChange={(event) => onChange({ eventTo: event.target.value })} /></label>
        <label className="cx-cutoff-field"><span>{copy.cutoff}</span><input type="datetime-local" value={filters.cutoff} onChange={(event) => onChange({ cutoff: event.target.value })} /></label>
      </div>
      <p className="cx-known-at">{interpolate(copy.knownAt, { date: cutoffLabel })}</p>
    </section>
  );
}
