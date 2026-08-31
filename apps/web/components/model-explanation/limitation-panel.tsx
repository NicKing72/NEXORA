import { ShieldAlert } from "lucide-react";

import type { ExplanationRun } from "@/lib/explanation-types";
import { ui } from "@/lib/i18n";

export function LimitationPanel({ run }: Readonly<{ run: ExplanationRun }>) {
  const copy = ui.modelExplanation.limitations;
  return (
    <section className="mx-panel mx-limitations">
      <div className="mx-section-heading"><div><span>{copy.index}</span><h2>{copy.title}</h2></div><ShieldAlert size={18} /></div>
      <ul>{run.limitations.map((item) => <li key={item}>{copy.labels[item as keyof typeof copy.labels] ?? item}</li>)}</ul>
    </section>
  );
}
