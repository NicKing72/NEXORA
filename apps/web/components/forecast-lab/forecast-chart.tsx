"use client";

import type { ECharts, EChartsOption } from "echarts";
import { useEffect, useRef, useState } from "react";

import type { ForecastRun } from "@/lib/forecast-types";
import { interpolate, ui } from "@/lib/i18n";

export function ForecastChart({ run }: Readonly<{ run: ForecastRun }>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [chart, setChart] = useState<ECharts | null>(null);
  const copy = ui.forecastLab.chart;

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
    const forecast = run.forecast_points;
    const lower95 = forecast.map((point) => [point.timestamp, point.lower_95]);
    const band95 = forecast.map((point) => [point.timestamp, point.lower_95 === null || point.upper_95 === null ? null : point.upper_95 - point.lower_95]);
    const lower80 = forecast.map((point) => [point.timestamp, point.lower_80]);
    const band80 = forecast.map((point) => [point.timestamp, point.lower_80 === null || point.upper_80 === null ? null : point.upper_80 - point.lower_80]);
    const option: EChartsOption = {
      animationDuration: 450,
      backgroundColor: "transparent",
      grid: { left: 58, right: 36, top: 44, bottom: 72 },
      legend: { top: 4, right: 4, textStyle: { color: "#9eaaa7", fontSize: 11 }, itemWidth: 18 },
      tooltip: { trigger: "axis", backgroundColor: "rgba(13,17,18,.97)", borderColor: "#2a3535", textStyle: { color: "#f0f3f1" } },
      xAxis: { type: "time", axisLabel: { color: "#7f8b89", hideOverlap: true }, axisLine: { lineStyle: { color: "#2a3334" } } },
      yAxis: { type: "value", axisLabel: { color: "#7f8b89" }, splitLine: { lineStyle: { color: "rgba(75,89,87,.18)" } } },
      dataZoom: [
        { type: "inside", filterMode: "none" },
        { type: "slider", bottom: 16, height: 22, borderColor: "#252d2e", backgroundColor: "#0d1112", fillerColor: "rgba(140,198,189,.12)", handleStyle: { color: "#8cc6bd" }, textStyle: { color: "#697573" } },
      ],
      series: [
        { name: copy.interval95, type: "line", stack: "interval95", data: lower95, symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, tooltip: { show: false } },
        { name: copy.interval95, type: "line", stack: "interval95", data: band95, symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(140,198,189,.08)" }, tooltip: { show: false } },
        { name: copy.interval80, type: "line", stack: "interval80", data: lower80, symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, tooltip: { show: false } },
        { name: copy.interval80, type: "line", stack: "interval80", data: band80, symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(140,198,189,.17)" }, tooltip: { show: false } },
        { name: copy.history, type: "line", data: run.history.map((point) => [point.date, point.demand]), connectNulls: false, showSymbol: false, lineStyle: { color: "#75817f", width: 1.5 }, itemStyle: { color: "#75817f" } },
        { name: copy.forecast, type: "line", data: forecast.map((point) => [point.timestamp, point.forecast]), showSymbol: false, lineStyle: { color: "#a2ded4", width: 2.4 }, itemStyle: { color: "#a2ded4" }, markLine: { symbol: "none", label: { formatter: copy.cutoff, color: "#d7dfdc", fontSize: 10 }, lineStyle: { color: "#697573", type: "dashed" }, data: [{ xAxis: run.data_cutoff }] } },
      ],
    };
    chart.setOption(option, { notMerge: true });
  }, [chart, copy, run]);

  const intervalCount = run.preprocessing.interval_residual_count ?? 0;
  const hasIntervals = run.forecast_points.some((point) => point.lower_80 !== null);
  return <section className="fx-panel fx-chart-panel"><div className="fx-heading"><div><span className="section-index">{copy.index}</span><h2>{copy.title}</h2></div><small>{hasIntervals ? interpolate(copy.method, { count: intervalCount }) : copy.insufficient}</small></div><div ref={containerRef} className="fx-chart" role="img" aria-label={copy.title} /><span className="fx-chart-hint">{copy.zoom}</span></section>;
}
