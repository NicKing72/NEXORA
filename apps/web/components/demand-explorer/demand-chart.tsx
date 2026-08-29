"use client";

import type { ECharts, EChartsOption } from "echarts";
import { useEffect, useMemo, useRef, useState } from "react";

import type { EventCounts, SeriesPoint } from "@/lib/series-types";
import { formatMetric, formatSeriesPeriod } from "@/lib/series-formatters";
import { interpolate, ui } from "@/lib/i18n";

export type EventVisibility = Record<keyof EventCounts, boolean>;

type DemandChartProps = {
  points: SeriesPoint[];
  frequency: string;
  visibility: EventVisibility;
  onVisibilityChange: (event: keyof EventCounts, visible: boolean) => void;
};

type TooltipEntry = {
  axisValue?: number | string;
};

const EVENT_STYLES: Record<keyof EventCounts, { color: string; symbol: string }> = {
  outlier: { color: "#d8ab73", symbol: "diamond" },
  missing: { color: "#a4afad", symbol: "emptyCircle" },
  stockout: { color: "#cf8176", symbol: "pin" },
  zero: { color: "#697573", symbol: "circle" },
};

function axisDateKey(axisValue: number | string | undefined): string | null {
  if (axisValue === undefined) return null;
  const parsed = new Date(axisValue);
  if (Number.isNaN(parsed.getTime())) return null;
  const year = parsed.getFullYear();
  const month = String(parsed.getMonth() + 1).padStart(2, "0");
  const day = String(parsed.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function qualityLine(label: string, count: number): string {
  return `<div class="dx-tooltip-row"><span>${label}</span><strong>${formatMetric(count, 0)}</strong></div>`;
}

export function DemandChart({
  points,
  frequency,
  visibility,
  onVisibilityChange,
}: Readonly<DemandChartProps>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [chart, setChart] = useState<ECharts | null>(null);
  const eventCopy = ui.demandExplorer.chart.seriesNames;
  const toggleCopy = ui.demandExplorer.chart.toggles;
  const tooltipCopy = ui.demandExplorer.chart.tooltip;
  const pointByDate = useMemo(
    () => new Map(points.map((point) => [point.date.slice(0, 10), point])),
    [points],
  );
  const validDemand = useMemo(
    () => points.flatMap((point) => point.demand === null ? [] : [point.demand]),
    [points],
  );
  const minimum = validDemand.length ? Math.min(...validDemand) : 0;
  const maximum = validDemand.length ? Math.max(...validDemand) : 1;
  const missingBaseline = minimum - Math.max((maximum - minimum) * 0.06, 1);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    let disposed = false;
    let instance: ECharts | null = null;
    void import("echarts").then((echarts) => {
      if (disposed) return;
      instance = echarts.init(element, undefined, { renderer: "canvas" });
      setChart(instance);
    });
    const observer = new ResizeObserver(() => instance?.resize());
    observer.observe(element);
    return () => {
      disposed = true;
      observer.disconnect();
      instance?.dispose();
    };
  }, []);

  useEffect(() => {
    if (!chart) return;
    const markerSeries = (Object.keys(visibility) as Array<keyof EventCounts>)
      .filter((event) => visibility[event])
      .map((event) => ({
        name: eventCopy[event],
        type: "scatter" as const,
        symbol: EVENT_STYLES[event].symbol,
        symbolSize: event === "stockout" ? 12 : 8,
        itemStyle: { color: EVENT_STYLES[event].color, opacity: 0.82 },
        data: points
          .filter((point) => point.events[event] > 0 || (event === "missing" && point.demand === null))
          .map((point) => ({
            value: [point.date, point.demand ?? missingBaseline],
            eventCount: point.events[event],
          })),
        z: 5,
      }));
    const partialSeries = {
      name: tooltipCopy.partial,
      type: "scatter" as const,
      symbol: "emptyDiamond",
      symbolSize: 15,
      itemStyle: { color: "#d9bd79", opacity: 0.95 },
      data: points
        .filter((point) => point.is_partial)
        .map((point) => [point.date, point.demand ?? missingBaseline]),
      z: 4,
    };
    const option: EChartsOption = {
      animationDuration: 420,
      aria: {
        enabled: true,
        label: { description: ui.demandExplorer.chart.accessibleDescription },
      },
      backgroundColor: "transparent",
      grid: { left: 54, right: 42, top: 34, bottom: 72 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(13, 17, 18, 0.96)",
        borderColor: "#2a3535",
        textStyle: { color: "#f0f3f1", fontSize: 12 },
        axisPointer: { type: "line", lineStyle: { color: "#4c5d5a" } },
        formatter: (parameters: unknown) => {
          const entries = Array.isArray(parameters) ? parameters as TooltipEntry[] : [];
          const key = axisDateKey(entries[0]?.axisValue);
          const point = key ? pointByDate.get(key) : undefined;
          if (!point) return "";
          const demand = point.demand === null ? tooltipCopy.noDemand : formatMetric(point.demand);
          const qualityRows = [
            point.events.outlier > 0 ? qualityLine(tooltipCopy.outliers, point.events.outlier) : "",
            point.events.stockout > 0 ? qualityLine(tooltipCopy.stockouts, point.events.stockout) : "",
            point.events.missing > 0 ? qualityLine(tooltipCopy.sourceMissing, point.events.missing) : "",
            point.events.zero > 0 ? qualityLine(tooltipCopy.sourceZeros, point.events.zero) : "",
          ].join("");
          const partial = point.is_partial
            ? `<div class="dx-tooltip-partial">${interpolate(tooltipCopy.partialCoverage, {
                observed: point.observed_source_periods,
                expected: point.expected_source_periods,
                coverage: formatMetric(point.coverage_ratio * 100),
              })}</div>`
            : "";
          return [
            `<div class="dx-tooltip-title">${formatSeriesPeriod(point.date, frequency)}</div>`,
            `<div class="dx-tooltip-demand"><span>${tooltipCopy.demand}</span><strong>${demand}</strong></div>`,
            partial,
            qualityRows ? `<div class="dx-tooltip-quality"><b>${tooltipCopy.quality}</b>${qualityRows}</div>` : "",
          ].join("");
        },
      },
      xAxis: {
        type: "time",
        axisLine: { lineStyle: { color: "#2a3334" } },
        axisLabel: { color: "#7f8b89", hideOverlap: true, fontSize: 11 },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        name: ui.demandExplorer.chart.demand,
        nameTextStyle: { color: "#7f8b89", fontSize: 11, padding: [0, 0, 8, 0] },
        axisLabel: { color: "#7f8b89", fontSize: 11 },
        splitLine: { lineStyle: { color: "rgba(75, 89, 87, 0.18)" } },
      },
      dataZoom: [
        { type: "inside", filterMode: "none", zoomOnMouseWheel: true, moveOnMouseMove: true },
        {
          type: "slider",
          filterMode: "none",
          bottom: 16,
          height: 22,
          borderColor: "#252d2e",
          backgroundColor: "#0d1112",
          fillerColor: "rgba(140, 198, 189, 0.12)",
          handleStyle: { color: "#8cc6bd", borderColor: "#8cc6bd" },
          textStyle: { color: "#697573", fontSize: 10 },
        },
      ],
      series: [
        {
          name: eventCopy.demand,
          type: "line",
          data: points.map((point) => [point.date, point.demand]),
          connectNulls: false,
          showSymbol: false,
          smooth: false,
          lineStyle: { color: "#8cc6bd", width: 2 },
          itemStyle: { color: "#8cc6bd" },
          areaStyle: { color: "rgba(140, 198, 189, 0.045)" },
          emphasis: { focus: "series" },
          z: 3,
        },
        partialSeries,
        ...markerSeries,
      ],
    };
    chart.setOption(option, { notMerge: true });
  }, [chart, eventCopy, frequency, missingBaseline, pointByDate, points, tooltipCopy, visibility]);

  return (
    <section className="dx-chart-panel" aria-labelledby="dx-chart-title">
      <div className="dx-section-heading dx-chart-heading">
        <div>
          <span className="section-index">{ui.demandExplorer.chart.index}</span>
          <h2 id="dx-chart-title">{ui.demandExplorer.chart.title}</h2>
          <p>{ui.demandExplorer.chart.subtitle}</p>
        </div>
        <div className="dx-event-toggles" aria-label={ui.demandExplorer.chart.events}>
          {(Object.keys(visibility) as Array<keyof EventCounts>).map((event) => (
            <label key={event}>
              <input type="checkbox" checked={visibility[event]} onChange={(change) => onVisibilityChange(event, change.target.checked)} />
              <i style={{ background: EVENT_STYLES[event].color }} />
              {toggleCopy[event]}
            </label>
          ))}
        </div>
      </div>
      <div ref={containerRef} className="dx-chart" role="img" aria-label={ui.demandExplorer.chart.title} />
      <span className="dx-zoom-hint">{ui.demandExplorer.chart.zoomHint}</span>
    </section>
  );
}
