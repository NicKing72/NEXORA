import type { ForecastRequest } from "@/lib/forecast-types";
import { ui } from "@/lib/i18n";
import type { ReadyDatasetSummary, SeriesDimensions, SeriesRequestFrequency } from "@/lib/series-types";

type ForecastSelectorProps = {
  datasets: ReadyDatasetSummary[];
  dimensions: SeriesDimensions;
  request: ForecastRequest;
  disabled: boolean;
  onChange: (patch: Partial<ForecastRequest>) => void;
};

export function ForecastSelector({ datasets, dimensions, request, disabled, onChange }: Readonly<ForecastSelectorProps>) {
  const copy = ui.forecastLab.selector;
  const frequencies = ui.demandExplorer.selector.frequencyOptions;
  const selectedProduct = dimensions.products.find((item) => item.value === request.product);
  const categories = selectedProduct
    ? dimensions.categories.filter((item) => selectedProduct.categories.includes(item.value))
    : dimensions.categories;
  const selectedLabel = [
    request.product || copy.allProducts,
    request.location || copy.allLocations,
    frequencies[request.frequency],
  ].join(" · ");

  return (
    <section className="fx-panel fx-selector" aria-labelledby="fx-selector-title">
      <div className="fx-heading">
        <div><span className="section-index">{copy.index}</span><h2 id="fx-selector-title">{copy.title}</h2></div>
        <strong>{selectedLabel}</strong>
      </div>
      <div className="fx-filter-grid">
        <label><span>{copy.dataset}</span><select value={request.dataset_id} disabled={disabled} onChange={(event) => onChange({ dataset_id: event.target.value })}>{datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name}</option>)}</select></label>
        <label><span>{copy.product}</span><select value={request.product ?? ""} disabled={disabled} onChange={(event) => onChange({ product: event.target.value || null, category: null })}><option value="">{copy.allProducts}</option>{dimensions.products.map((item) => <option key={item.value} value={item.value}>{item.value}</option>)}</select></label>
        <label><span>{copy.location}</span><select value={request.location ?? ""} disabled={disabled} onChange={(event) => onChange({ location: event.target.value || null })}><option value="">{copy.allLocations}</option>{dimensions.locations.map((item) => <option key={item.value} value={item.value}>{item.value}</option>)}</select></label>
        {dimensions.categories.length > 0 && <label><span>{copy.category}</span><select value={request.category ?? ""} disabled={disabled} onChange={(event) => onChange({ category: event.target.value || null })}><option value="">{copy.allCategories}</option>{categories.map((item) => <option key={item.value} value={item.value}>{item.value}</option>)}</select></label>}
        <label><span>{copy.frequency}</span><select value={request.frequency} disabled={disabled} onChange={(event) => onChange({ frequency: event.target.value as SeriesRequestFrequency })}>{dimensions.available_frequencies.map((frequency) => <option key={frequency} value={frequency}>{frequencies[frequency]}</option>)}</select></label>
        <label><span>{copy.horizon}</span><div className="fx-horizon"><input type="number" min={1} max={365} value={request.horizon} disabled={disabled} onChange={(event) => onChange({ horizon: Math.min(365, Math.max(1, Number(event.target.value) || 1)) })} /><small>{copy.horizonUnit}</small></div></label>
      </div>
    </section>
  );
}
