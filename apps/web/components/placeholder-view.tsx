import { ArrowLeft, ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { ui } from "@/lib/i18n";
import type { NavigationSection } from "@/lib/navigation";

export function PlaceholderView({ section }: Readonly<{ section: NavigationSection }>) {
  const Icon = section.icon;

  return (
    <div className="workspace placeholder-workspace">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">{ui.placeholder.eyebrow}</span>
          <h1>{section.label}</h1>
          <p>{section.description}</p>
        </div>
      </header>

      <section className="placeholder-stage">
        <div className="placeholder-grid" aria-hidden="true" />
        <span className="placeholder-icon"><Icon size={26} strokeWidth={1.4} /></span>
        <span className="section-index">{ui.placeholder.reserved}</span>
        <h2>{ui.placeholder.title}</h2>
        <p>{ui.placeholder.description}</p>
        <div className="placeholder-actions">
          <Link className="secondary-action" href="/command-center">
            <ArrowLeft size={15} /> {ui.placeholder.returnToCommand}
          </Link>
          <span className="text-action text-action--muted">
            {ui.placeholder.milestone} <ArrowUpRight size={14} />
          </span>
        </div>
      </section>

      <footer className="workspace-footer">
        <span>{ui.placeholder.status}</span>
        <span>{ui.brand.subtitle}</span>
      </footer>
    </div>
  );
}
