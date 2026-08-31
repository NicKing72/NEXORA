import { BrainCircuit, ShieldCheck } from "lucide-react";

import { ui } from "@/lib/i18n";

export function ExplanationHeader() {
  const copy = ui.modelExplanation.header;
  return (
    <header className="mx-header">
      <div>
        <span className="eyebrow">{copy.eyebrow}</span>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
      </div>
      <div className="mx-boundary-badges">
        <span><BrainCircuit size={15} />{copy.badge}</span>
        <span><ShieldCheck size={15} />{copy.boundary}</span>
      </div>
    </header>
  );
}
