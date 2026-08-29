import type { ForecastModelResult } from "@/lib/forecast-types";
import { ui } from "@/lib/i18n";
import { formatMetric } from "@/lib/series-formatters";

export function ModelDetail({ model }: Readonly<{ model: ForecastModelResult | null }>) {
  const copy = ui.forecastLab.detail;
  if (!model) return <section className="fx-panel fx-model-detail"><span className="section-index">{copy.index}</span><p className="fx-muted">{copy.selectHint}</p></section>;
  const value = (key: string) => {
    const item = model.parameters[key];
    if (item === null || item === undefined) return copy.noParameter;
    if (key === "initialization_method" && item === "estimated") return copy.parameterValues.estimated;
    if (key === "initialization_method" && item === "first_observation") return copy.parameterValues.firstObservation;
    if (key === "initialization_method" && item === "first_two_observations") return copy.parameterValues.firstTwoObservations;
    if (key === "initialization_method" && item === "heuristic_two_cycle") return copy.parameterValues.heuristicTwoCycle;
    if (key === "engine" && item === "statsmodels") return copy.parameterValues.statsmodels;
    if (key === "engine" && item === "native_baseline") return copy.parameterValues.nativeBaseline;
    if (key === "engine" && item === "numpy_fallback") return copy.parameterValues.numpyFallback;
    if (key === "engine" && item === "numpy_deterministic_fallback") return copy.parameterValues.numpyFallback;
    if (key === "parameter_source" && item === "optimized") return copy.parameterValues.optimized;
    if (key === "parameter_source" && item === "optimized_grid_search") return copy.parameterValues.optimizedGridSearch;
    if (key === "parameter_source" && item === "deterministic_rule") return copy.parameterValues.deterministicRule;
    if (key === "parameter_source" && item === "configured_window") return copy.parameterValues.configuredWindow;
    return typeof item === "number" ? formatMetric(item, 6) : String(item);
  };
  return <section className="fx-panel fx-model-detail"><div className="fx-heading"><div><span className="section-index">{copy.index}</span><h2>{copy.title}</h2></div></div><div className="fx-parameter-grid"><div><span>{copy.alpha}</span><strong>{value("alpha")}</strong></div><div><span>{copy.beta}</span><strong>{value("beta")}</strong></div><div><span>{copy.gamma}</span><strong>{value("gamma")}</strong></div><div><span>{copy.period}</span><strong>{value("seasonal_period")}</strong></div><div><span>{copy.initialization}</span><strong>{value("initialization_method")}</strong></div><div><span>{copy.engine}</span><strong>{value("engine")}</strong></div><div><span>{copy.parameterSource}</span><strong>{value("parameter_source")}</strong></div></div></section>;
}
