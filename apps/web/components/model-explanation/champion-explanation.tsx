import { Award, Scale, ShieldAlert } from "lucide-react";

import type { ExplanationRun } from "@/lib/explanation-types";
import { interpolate, ui } from "@/lib/i18n";

function percent(value: number | null | undefined) {
  return value == null ? "—" : `${(value * 100).toFixed(2)}%`;
}

export function ChampionExplanation({ run }: Readonly<{ run: ExplanationRun }>) {
  const copy = ui.modelExplanation.champion;
  const champion = run.source_snapshot.champion;
  const folds = run.source_snapshot.backtesting.folds.length;
  const reason = champion.reason
    ? ui.forecastLab.champion.reasons[
      champion.reason as keyof typeof ui.forecastLab.champion.reasons
    ] ?? champion.reason
    : "—";
  const name = ui.forecastLab.modelNames[
    champion.model_name as keyof typeof ui.forecastLab.modelNames
  ] ?? champion.model_name;
  return (
    <section className="mx-panel mx-champion">
      <div className="mx-section-heading">
        <div><span>{copy.index}</span><h2>{copy.title}</h2></div>
        <span className="mx-champion-badge"><Award size={15} />Champion</span>
      </div>
      <div className="mx-champion-lead">
        <div><small>{copy.detected}</small><strong>{name}</strong><p>{interpolate(copy.detectedText, { model: name })}</p></div>
        <div><small>{copy.selected}</small><strong>{reason}</strong><p>{copy.score}: {percent(champion.metrics.wmape)}</p></div>
      </div>
      <div className="mx-explanation-grid">
        <article><Scale size={17} /><span><small>{copy.evidence}</small><p>{interpolate(copy.evidenceText, { folds })}</p></span></article>
        <article><ShieldAlert size={17} /><span><small>{copy.cannot}</small><p>{copy.cannotText}</p></span></article>
      </div>
    </section>
  );
}
