import { ArrowRight, DatabaseZap } from "lucide-react";
import Link from "next/link";

import { ui } from "@/lib/i18n";

export function ExplorerEmptyState() {
  return (
    <section className="dx-empty" aria-labelledby="dx-empty-title">
      <span className="dx-empty-icon"><DatabaseZap size={26} /></span>
      <span className="section-index">{ui.demandExplorer.empty.index}</span>
      <h2 id="dx-empty-title">{ui.demandExplorer.empty.title}</h2>
      <p>{ui.demandExplorer.empty.description}</p>
      <Link className="dx-primary-action" href="/data-studio">
        {ui.demandExplorer.empty.action} <ArrowRight size={15} />
      </Link>
    </section>
  );
}
