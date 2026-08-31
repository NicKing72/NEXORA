import {
  buildDecisionCenterHrefFromRun,
  parseDecisionHandoff,
  type DecisionRunContext,
} from "./decision-handoff.ts";

export const DECISION_WORKSPACE_EVENT = "nexora:decision-workspace-updated";
export const DECISION_WORKSPACE_STORAGE_KEY = "nexora:last-decision-workspace";

export type SessionStorageLike = Pick<Storage, "getItem" | "setItem">;

export function isRestorableDecisionWorkspace(href: string | null): href is string {
  if (!href) return false;
  try {
    const url = new URL(href, "http://nexora.local");
    if (url.origin !== "http://nexora.local" || url.pathname !== "/decision-center") return false;
    const context = parseDecisionHandoff(url.search);
    return Boolean(context.forecastRunId && context.decisionRunId);
  } catch {
    return false;
  }
}

export function readDecisionWorkspace(storage: SessionStorageLike) {
  const stored = storage.getItem(DECISION_WORKSPACE_STORAGE_KEY);
  return isRestorableDecisionWorkspace(stored) ? stored : "/decision-center";
}

export function persistDecisionWorkspace(storage: SessionStorageLike, href: string) {
  if (!isRestorableDecisionWorkspace(href)) return false;
  storage.setItem(DECISION_WORKSPACE_STORAGE_KEY, href);
  return true;
}

export function rememberDecisionWorkspace(run: DecisionRunContext) {
  const href = buildDecisionCenterHrefFromRun(run);
  if (!persistDecisionWorkspace(window.sessionStorage, href)) return;
  window.history.replaceState(null, "", href);
  window.dispatchEvent(new CustomEvent(DECISION_WORKSPACE_EVENT, { detail: href }));
}
