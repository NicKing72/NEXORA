import type { ExplanationModel } from "@/lib/explanation-types";
import { ui } from "@/lib/i18n";

type Props = {
  models: ExplanationModel[];
  selectedId: number | null;
  onSelect: (model: ExplanationModel) => void;
};

function metric(value: number | null | undefined, percentage = false) {
  if (value == null) return "—";
  return percentage ? `${(value * 100).toFixed(2)}%` : value.toFixed(2);
}

export function ModelComparison({ models, selectedId, onSelect }: Readonly<Props>) {
  const copy = ui.modelExplanation.comparison;
  return (
    <section className="mx-panel mx-comparison">
      <div className="mx-section-heading"><div><span>{copy.index}</span><h2>{copy.title}</h2></div></div>
      <div className="mx-table-scroll">
        <table>
          <thead><tr><th>{copy.rank}</th><th>{copy.model}</th><th>{copy.status}</th><th>{copy.wmape}</th><th>{copy.mae}</th><th>{copy.rmse}</th><th>{copy.mape}</th><th>{copy.smape}</th><th>{copy.bias}</th><th>{copy.folds}</th><th>{copy.observations}</th></tr></thead>
          <tbody>{models.map((model) => {
            const name = ui.forecastLab.modelNames[model.model_name as keyof typeof ui.forecastLab.modelNames] ?? model.model_name;
            return <tr key={model.id} className={selectedId === model.id ? "is-selected" : ""} onClick={() => onSelect(model)}>
              <td>{model.rank ?? "—"}</td>
              <td><button type="button" onClick={() => onSelect(model)}>{name}</button>{model.is_champion && <em>{copy.champion}</em>}{model.within_champion_tolerance && !model.is_champion && <small>{copy.tie}</small>}</td>
              <td>{ui.modelExplanation.status[model.status as keyof typeof ui.modelExplanation.status] ?? model.status}</td>
              <td>{metric(model.metrics.wmape, true)}</td><td>{metric(model.metrics.mae)}</td><td>{metric(model.metrics.rmse)}</td><td>{metric(model.metrics.mape, true)}</td><td>{metric(model.metrics.smape, true)}</td><td>{metric(model.metrics.bias)}</td><td>{model.valid_folds}</td><td>{model.observations ?? "—"}</td>
            </tr>;
          })}</tbody>
        </table>
      </div>
    </section>
  );
}
