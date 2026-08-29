export function formatMetric(value: number | null, maximumFractionDigits = 2): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("es-PE", { maximumFractionDigits }).format(value);
}

export function formatSeriesDate(value: string | null): string {
  if (!value) return "—";
  const normalized = value.includes("T") ? value : `${value}T00:00:00`;
  return new Intl.DateTimeFormat("es-PE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(normalized));
}

export function formatSignedPercent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatMetric(value)}%`;
}

export function formatSeriesPeriod(value: string, frequency: string): string {
  const normalized = value.includes("T") ? value : `${value}T00:00:00`;
  const parsed = new Date(normalized);
  if (frequency === "weekly") {
    const utc = new Date(Date.UTC(parsed.getFullYear(), parsed.getMonth(), parsed.getDate()));
    const weekday = utc.getUTCDay() || 7;
    utc.setUTCDate(utc.getUTCDate() + 4 - weekday);
    const yearStart = new Date(Date.UTC(utc.getUTCFullYear(), 0, 1));
    const week = Math.ceil((((utc.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
    return `Semana ${week}/${utc.getUTCFullYear()}`;
  }
  if (frequency === "monthly") {
    return new Intl.DateTimeFormat("es-PE", { month: "long", year: "numeric" }).format(parsed);
  }
  return formatSeriesDate(value);
}
