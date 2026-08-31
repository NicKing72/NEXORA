"use client";

import type { ECharts, EChartsOption } from "echarts";
import { useEffect, useRef, useState } from "react";

import type { ExplanationRun } from "@/lib/explanation-types";
import { ui } from "@/lib/i18n";

function number(value: unknown) {
  return typeof value === "number" ? value.toLocaleString("es-PE", { maximumFractionDigits: 2 }) : "—";
}

export function ForecastExplanation({ run }: Readonly<{ run: ExplanationRun }>) {
  const copy = ui.modelExplanation.forecast;
  const containerRef = useRef<HTMLDivElement>(null);
  const [chart, setChart] = useState<ECharts | null>(null);
  const output = run.source_snapshot.forecast_output;
  const summary = output.summary;
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
    return () => { disposed = true; observer.disconnect(); instance?.dispose(); };
  }, []);
  useEffect(() => {
    if (!chart) return;
    const lower95 = output.points.map((point) => [point.timestamp, point.lower_95]);
    const band95 = output.points.map((point) => [point.timestamp, point.width_95]);
    const lower80 = output.points.map((point) => [point.timestamp, point.lower_80]);
    const band80 = output.points.map((point) => [point.timestamp, point.width_80]);
    const option: EChartsOption = {
      animationDuration: 350,
      backgroundColor: "transparent",
      grid: { left: 58, right: 32, top: 42, bottom: 50 },
      legend: { top: 2, right: 4, textStyle: { color: "#9eaaa7" } },
      tooltip: { trigger: "axis", backgroundColor: "rgba(13,17,18,.97)", borderColor: "#2a3535", textStyle: { color: "#f0f3f1" } },
      xAxis: { type: "time", axisLabel: { color: "#7f8b89" }, axisLine: { lineStyle: { color: "#2a3334" } } },
      yAxis: { type: "value", axisLabel: { color: "#7f8b89" }, splitLine: { lineStyle: { color: "rgba(75,89,87,.18)" } } },
      dataZoom: [{ type: "inside" }],
      series: [
        { name: copy.interval95, type: "line", stack: "i95", data: lower95, symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, tooltip: { show: false } },
        { name: copy.interval95, type: "line", stack: "i95", data: band95, symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(140,198,189,.08)" }, tooltip: { show: false } },
        { name: copy.interval80, type: "line", stack: "i80", data: lower80, symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, tooltip: { show: false } },
        { name: copy.interval80, type: "line", stack: "i80", data: band80, symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(140,198,189,.16)" }, tooltip: { show: false } },
        { name: copy.forecast, type: "line", data: output.points.map((point) => [point.timestamp, point.forecast]), symbol: "circle", symbolSize: 5, lineStyle: { color: "#a2ded4", width: 2.3 }, itemStyle: { color: "#a2ded4" } },
      ],
    };
    chart.setOption(option, { notMerge: true });
  }, [chart, copy, output.points]);
  const trend = copy.trends[summary.trend.label as keyof typeof copy.trends] ?? summary.trend.label;
  const hasIntervals = summary.has_80_interval || summary.has_95_interval;
  return (
    <section className="mx-panel mx-forecast">
      <div className="mx-section-heading"><div><span>{copy.index}</span><h2>{copy.title}</h2></div></div>
      <div className="mx-forecast-stats"><div><small>{copy.start}</small><strong>{summary.start ?? "—"}</strong></div><div><small>{copy.end}</small><strong>{summary.end ?? "—"}</strong></div><div><small>{copy.total}</small><strong>{number(summary.total)}</strong></div><div><small>{copy.average}</small><strong>{number(summary.average)}</strong></div><div><small>{copy.minimum}</small><strong>{number(summary.minimum)}</strong></div><div><small>{copy.maximum}</small><strong>{number(summary.maximum)}</strong></div><div><small>{copy.trend}</small><strong>{trend}</strong></div></div>
      <div ref={containerRef} className="mx-forecast-chart" role="img" aria-label={copy.title} />
      <p className="mx-interval-note">{hasIntervals ? copy.intervalNote : copy.noIntervals}</p>
    </section>
  );
}
