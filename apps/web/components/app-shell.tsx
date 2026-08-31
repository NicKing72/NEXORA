"use client";

import { Menu, Radio, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import {
  DECISION_WORKSPACE_EVENT,
  readDecisionWorkspace,
} from "@/lib/decision-workspace";
import { ui } from "@/lib/i18n";
import { sections } from "@/lib/navigation";

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [decisionHref, setDecisionHref] = useState("/decision-center");

  useEffect(() => {
    const synchronizeDecisionHref = () => {
      setDecisionHref(readDecisionWorkspace(window.sessionStorage));
    };
    synchronizeDecisionHref();
    window.addEventListener(DECISION_WORKSPACE_EVENT, synchronizeDecisionHref);
    return () => window.removeEventListener(DECISION_WORKSPACE_EVENT, synchronizeDecisionHref);
  }, []);

  return (
    <div className="app-shell">
      <header className="mobile-header">
        <Link className="brand brand--mobile" href="/" aria-label={ui.brand.homeLabel}>
          <span className="brand-mark">N</span>
          <span>NEXORA</span>
        </Link>
        <button
          className="icon-button"
          type="button"
          aria-label={isMenuOpen ? ui.navigation.close : ui.navigation.open}
          aria-expanded={isMenuOpen}
          onClick={() => setIsMenuOpen((open) => !open)}
        >
          {isMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>

      <aside className={`sidebar${isMenuOpen ? " sidebar--open" : ""}`}>
        <div className="sidebar-top">
          <Link className="brand" href="/" onClick={() => setIsMenuOpen(false)}>
            <span className="brand-mark">N</span>
            <span className="brand-copy">
              <strong>NEXORA</strong>
              <small>{ui.brand.subtitle}</small>
            </span>
          </Link>

          <nav className="primary-nav" aria-label={ui.navigation.label}>
            <span className="nav-label">{ui.navigation.workspace}</span>
            {sections.map((item) => {
              const isActive =
                pathname === `/${item.slug}` ||
                (item.slug === "command-center" && pathname === "/");
              const Icon = item.icon;

              return (
                <Link
                  className={`nav-link${isActive ? " nav-link--active" : ""}`}
                  href={item.slug === "decision-center" ? decisionHref : `/${item.slug}`}
                  key={item.slug}
                  onClick={() => setIsMenuOpen(false)}
                >
                  <Icon aria-hidden="true" size={17} strokeWidth={1.7} />
                  <span>{item.label}</span>
                  {isActive && <span className="active-pulse" aria-hidden="true" />}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="sidebar-status">
          <Radio size={15} aria-hidden="true" />
          <span>
            <strong>{ui.shell.foundationMode}</strong>
            <small>{ui.shell.coreReady}</small>
          </span>
          <span className="status-dot" aria-hidden="true" />
        </div>
      </aside>

      {isMenuOpen && (
        <button
          className="sidebar-scrim"
          aria-label={ui.navigation.close}
          onClick={() => setIsMenuOpen(false)}
        />
      )}

      <main className="main-surface">{children}</main>
    </div>
  );
}
