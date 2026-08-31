type Point = { timestamp?: unknown; forecast?: unknown; lower_80?: unknown; upper_80?: unknown };

export function ReportForecastVisual({ points }: Readonly<{ points: Point[] }>) {
  const values = points.map((item) => Number(item.forecast)).filter(Number.isFinite);
  if (values.length < 2) return null;
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const span = maximum - minimum || 1;
  const coordinates = values.map((value, index) => {
    const x = (index / (values.length - 1)) * 100;
    const y = 88 - ((value - minimum) / span) * 68;
    return `${x},${y}`;
  }).join(" ");
  return (
    <div className="rp-forecast-visual" aria-label="Trayectoria del forecast persistido">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img">
        <line x1="0" y1="88" x2="100" y2="88" />
        <polyline points={coordinates} />
      </svg>
      <div><span>{String(points[0]?.timestamp ?? "").slice(0, 10)}</span><span>{String(points.at(-1)?.timestamp ?? "").slice(0, 10)}</span></div>
    </div>
  );
}
