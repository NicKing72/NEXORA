import { ArrowLeft, ArrowUpRight } from "lucide-react";
import Link from "next/link";

import type { NavigationSection } from "@/lib/navigation";

export function PlaceholderView({ section }: Readonly<{ section: NavigationSection }>) {
  const Icon = section.icon;

  return (
    <div className="workspace placeholder-workspace">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">NEXORA workspace / Foundation</span>
          <h1>{section.label}</h1>
          <p>{section.description}</p>
        </div>
      </header>

      <section className="placeholder-stage">
        <div className="placeholder-grid" aria-hidden="true" />
        <span className="placeholder-icon"><Icon size={26} strokeWidth={1.4} /></span>
        <span className="section-index">Module reserved</span>
        <h2>Designed for the next operational layer.</h2>
        <p>
          The workspace architecture is in place. Product logic and connected data
          will be added in their corresponding milestones.
        </p>
        <div className="placeholder-actions">
          <Link className="secondary-action" href="/command-center">
            <ArrowLeft size={15} /> Return to Command Center
          </Link>
          <span className="text-action text-action--muted">
            Milestone 01 <ArrowUpRight size={14} />
          </span>
        </div>
      </section>

      <footer className="workspace-footer">
        <span>Module status: structure ready</span>
        <span>Demand Intelligence System</span>
      </footer>
    </div>
  );
}
