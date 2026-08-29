import {
  apiErrorMessages,
  es,
  frequencyLabels,
  qualityIssueLabels,
  qualityIssueMessages,
} from "@/lib/i18n/es";

export const dictionaries = { es } as const;
export type Locale = keyof typeof dictionaries;
export const defaultLocale: Locale = "es";
export const ui = dictionaries[defaultLocale];

export function interpolate(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template,
  );
}

export function translateQualityIssue(code: string, count: number): string {
  return qualityIssueMessages[code]?.(count) ?? ui.dataStudio.validate.unknownIssue;
}

export function translateQualityIssueLabel(code: string): string {
  return qualityIssueLabels[code] ?? ui.dataStudio.validate.unknownIssueLabel;
}

export function translateApiError(code?: string): string {
  return (code && apiErrorMessages[code]) || ui.dataStudio.errors.requestFailed;
}

export function translateFrequency(frequency: string): string {
  return frequencyLabels[frequency] ?? frequency;
}

export function canonicalRoleLabel(role: string): string {
  if (role === "external") return ui.dataStudio.map.external;
  if (role === "ignore") return ui.dataStudio.map.ignore;
  const roleCopy = ui.dataStudio.map.roles[role as keyof typeof ui.dataStudio.map.roles];
  return roleCopy?.label ?? role.replaceAll("_", " ");
}
