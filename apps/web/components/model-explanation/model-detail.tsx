import { FunctionSquare, Settings2 } from "lucide-react";

import type { ExplanationModel } from "@/lib/explanation-types";
import { ui } from "@/lib/i18n";

export function ExplanationModelDetail({ model }: Readonly<{ model: ExplanationModel | null }>) {
  const copy = ui.modelExplanation.model;
  if (!model) return <section className="mx-panel mx-model-detail"><div className="mx-section-heading"><div><span>{copy.index}</span><h2>{copy.title}</h2></div></div><p>{copy.select}</p></section>;
  const definition = model.explanation;
  return (
    <section className="mx-panel mx-model-detail">
      <div className="mx-section-heading"><div><span>{copy.index}</span><h2>{definition.name}</h2></div><small>{definition.family}</small></div>
      <div className="mx-formula"><FunctionSquare size={19} /><span><small>{copy.formula}</small><code>{definition.formula}</code></span></div>
      <div className="mx-model-grid">
        <article><small>{copy.patterns}</small><ul>{definition.patterns.map((item) => <li key={item}>{item}</li>)}</ul></article>
        <article><small>{copy.inputs}</small><ul>{definition.inputs.map((item) => <li key={item}>{item}</li>)}</ul></article>
        <article><small>{copy.strengths}</small><ul>{definition.strengths.map((item) => <li key={item}>{item}</li>)}</ul></article>
        <article><small>{copy.limitations}</small><ul>{definition.limitations.map((item) => <li key={item}>{item}</li>)}</ul></article>
      </div>
      <div className="mx-parameters"><div><Settings2 size={16} /><strong>{copy.parameters}</strong></div>{definition.parameters_available ? <dl>{Object.entries(definition.parameters).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value == null ? "—" : String(value)}</dd></div>)}</dl> : <p>{copy.unavailable}</p>}<small>{copy.engine}: {definition.engine ?? copy.unavailable} · {copy.parameterSource}: {definition.parameter_source ?? copy.unavailable}</small></div>
    </section>
  );
}
