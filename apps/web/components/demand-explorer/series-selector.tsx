import type {
  ReadyDatasetSummary,
  SeriesDimensions,
  SeriesFilters,
  SeriesRequestFrequency,
} from "@/lib/series-types";
import { interpolate, translateFrequency, ui } from "@/lib/i18n";

type SeriesSelectorProps = {
  datasets: ReadyDatasetSummary[];
  dimensions: SeriesDimensions;
  filters: SeriesFilters;
  isLoading: boolean;
  onChange: (patch: Partial<SeriesFilters>) => void;
};

export function SeriesSelector({ datasets, dimensions, filters, isLoading, onChange }: Readonly<SeriesSelectorProps>) {
  const product = dimensions.products.find((item) => item.value === filters.product);
  const categories = product
    ? dimensions.categories.filter((item) => product.categories.includes(item.value))
    : dimensions.categories;
  const frequencyCopy = ui.demandExplorer.selector.frequencyOptions;
  const selectedLabel = [
    filters.product || ui.demandExplorer.selector.allProducts,
    filters.location || ui.demandExplorer.selector.allLocations,
    frequencyCopy[filters.frequency],
  ].join(" · ");

  function changeProduct(value: string) {
    const nextProduct = dimensions.products.find((item) => item.value === value);
    const category = filters.category && nextProduct?.categories.includes(filters.category)
      ? filters.category
      : "";
    onChange({ product: value, category });
  }

  return (
    <section className="dx-selector" aria-labelledby="dx-selector-title">
      <div className="dx-section-heading">
        <div>
          <span className="section-index">{ui.demandExplorer.selector.index}</span>
          <h2 id="dx-selector-title">{ui.demandExplorer.selector.title}</h2>
        </div>
        <span className="dx-source-frequency">
          {interpolate(ui.demandExplorer.selector.sourceFrequency, {
            frequency: translateFrequency(dimensions.source_frequency),
          })}
        </span>
      </div>

      <div className="dx-filter-grid">
        <label>
          <span>{ui.demandExplorer.selector.dataset}</span>
          <select value={filters.datasetId} disabled={isLoading} onChange={(event) => onChange({ datasetId: event.target.value })}>
            {datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name}</option>)}
          </select>
        </label>
        <label>
          <span>{ui.demandExplorer.selector.product}</span>
          <select value={filters.product} disabled={isLoading} onChange={(event) => changeProduct(event.target.value)}>
            <option value="">{ui.demandExplorer.selector.allProducts}</option>
            {dimensions.products.map((item) => <option key={item.value} value={item.value}>{item.value}</option>)}
          </select>
        </label>
        <label>
          <span>{ui.demandExplorer.selector.location}</span>
          <select value={filters.location} disabled={isLoading} onChange={(event) => onChange({ location: event.target.value })}>
            <option value="">{ui.demandExplorer.selector.allLocations}</option>
            {dimensions.locations.map((item) => <option key={item.value} value={item.value}>{item.value}</option>)}
          </select>
        </label>
        {dimensions.categories.length > 0 && (
          <label>
            <span>{ui.demandExplorer.selector.category}</span>
            <select value={filters.category} disabled={isLoading} onChange={(event) => onChange({ category: event.target.value })}>
              <option value="">{ui.demandExplorer.selector.allCategories}</option>
              {categories.map((item) => <option key={item.value} value={item.value}>{item.value}</option>)}
            </select>
          </label>
        )}
        <label>
          <span>{ui.demandExplorer.selector.periodStart}</span>
          <input type="date" min={dimensions.first_date ?? undefined} max={filters.endDate || dimensions.last_date || undefined} value={filters.startDate} disabled={isLoading} onChange={(event) => onChange({ startDate: event.target.value })} />
        </label>
        <label>
          <span>{ui.demandExplorer.selector.periodEnd}</span>
          <input type="date" min={filters.startDate || dimensions.first_date || undefined} max={dimensions.last_date ?? undefined} value={filters.endDate} disabled={isLoading} onChange={(event) => onChange({ endDate: event.target.value })} />
        </label>
        <label>
          <span>{ui.demandExplorer.selector.frequency}</span>
          <select value={filters.frequency} disabled={isLoading} onChange={(event) => onChange({ frequency: event.target.value as SeriesRequestFrequency })}>
            {dimensions.available_frequencies.map((frequency) => (
              <option key={frequency} value={frequency}>{frequencyCopy[frequency]}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="dx-series-selection">
        <span>{ui.demandExplorer.selector.selected}</span>
        <strong>{selectedLabel}</strong>
      </div>
    </section>
  );
}
