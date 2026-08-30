import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { ui } from "@/lib/i18n";

import "./globals.css";
import "../styles/data-studio.css";
import "../styles/demand-explorer.css";
import "../styles/forecast-lab.css";
import "../styles/context-radar.css";
import "../styles/scenario-lab.css";
import "../styles/decision-center.css";
import "../styles/scor-diagnostic.css";

export const metadata: Metadata = {
  title: {
    default: ui.meta.title,
    template: "%s | NEXORA",
  },
  description: ui.meta.description,
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="es">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
