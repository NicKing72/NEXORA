import { Check } from "lucide-react";

import type { WorkflowStep } from "@/lib/data-studio-types";
import { ui } from "@/lib/i18n";

const steps: Array<{ id: WorkflowStep; index: string; label: string }> = [
  { id: "import", index: "01", label: ui.dataStudio.steps.import },
  { id: "map", index: "02", label: ui.dataStudio.steps.map },
  { id: "validate", index: "03", label: ui.dataStudio.steps.validate },
  { id: "ready", index: "04", label: ui.dataStudio.steps.ready },
];

export function WorkflowStepper({ current }: Readonly<{ current: WorkflowStep }>) {
  const activeIndex = steps.findIndex((step) => step.id === current);
  return (
    <ol className="ds-stepper" aria-label={ui.dataStudio.progressLabel}>
      {steps.map((step, index) => {
        const complete = index < activeIndex;
        const active = index === activeIndex;
        return (
          <li className={active ? "is-active" : complete ? "is-complete" : ""} key={step.id}>
            <span className="ds-step-marker">{complete ? <Check size={13} /> : step.index}</span>
            <span>{step.label}</span>
          </li>
        );
      })}
    </ol>
  );
}
