"use client";

import type { ECharts, EChartsOption } from "echarts";
import { useEffect, useRef, useState } from "react";

import type { ForecastRun } from "@/lib/forecast-types";
import { ui } from "@/lib/i18n";
import type { ScenarioRun } from "@/lib/scenario-types";

export function ScenarioChart({ forecast, scenario }: Readonly<{ forecast: ForecastRun; scenario: ScenarioRun }>) {
  const elementRef = useRef<HTMLDivElement>(null);
  const [chart, setChart] = useState<ECharts | null>(null);
  useEffect(() => {
    if (!elementRef.current) return;
    let disposed = false;
    let instance: ECharts | null = null;
    void import("echarts").then((library) => {
      if (disposed || !elementRef.current) return;
      instance = library.init(elementRef.current, undefined, { renderer: "canvas" });
      setChart(instance);
    });
    const observer = new ResizeObserver(() => instance?.resize());
    observer.observe(elementRef.current);
    return () => { disposed = true; observer.disconnect(); instance?.dispose(); };
  }, []);
  useEffect(() => {
    if (!chart) return;
    const copy = ui.scenarioLab.result;
    const affected: Array<[
      { xAxis: string; itemStyle: { color: string } },
      { xAxis: string },
    ]> = scenario.assumptions.map((item) => [
      { xAxis: item.start_at.slice(0, 10), itemStyle: { color: "rgba(216,171,115,.045)" } },
      { xAxis: (item.end_at ?? item.start_at).slice(0, 10) },
    ]);
    const lower95 = scenario.points.map((point) => [point.timestamp, point.lower_95]);
    const band95 = scenario.points.map((point) => [point.timestamp, point.lower_95 == null || point.upper_95 == null ? null : point.upper_95 - point.lower_95]);
    const option: EChartsOption = {
      animationDuration: 420,
      backgroundColor: "transparent",
      grid: { left: 58, right: 30, top: 52, bottom: 72 },
      legend: { top: 4, right: 4, textStyle: { color: "#a4afad" } },
      tooltip: { trigger: "axis", backgroundColor: "rgba(13,17,18,.98)", borderColor: "#2a3535", textStyle: { color: "#f0f3f1" } },
      xAxis: { type: "time", axisLabel: { color: "#7f8b89" }, axisLine: { lineStyle: { color: "#2a3334" } } },
      yAxis: { type: "value", axisLabel: { color: "#7f8b89" }, splitLine: { lineStyle: { color: "rgba(75,89,87,.18)" } } },
      dataZoom: [{ type: "inside", filterMode: "none" }, { type: "slider", bottom: 15, height: 22, borderColor: "#252d2e", backgroundColor: "#0d1112", fillerColor: "rgba(140,198,189,.12)", textStyle: { color: "#697573" } }],
      series: [
        { name: copy.history, type: "line", data: forecast.history.map((point) => [point.date, point.demand]), symbol: "none", connectNulls: false, lineStyle: { color: "#687471", width: 1.3 } },
        { name: "Intervalo 95%", type: "line", stack: "interval95", data: lower95, symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, tooltip: { show: false } },
        { name: "Intervalo 95%", type: "line", stack: "interval95", data: band95, symbol: "none", lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(140,198,189,.08)" }, tooltip: { show: false } },
        { name: copy.baseline, type: "line", data: scenario.points.map((point) => [point.timestamp, point.baseline]), symbol: "none", lineStyle: { color: "#8cc6bd", width: 2, type: "dashed" } },
        { name: copy.scenario, type: "line", data: scenario.points.map((point) => [point.timestamp, point.scenario]), symbol: "circle", symbolSize: 4, lineStyle: { color: "#d8ab73", width: 2.4 }, markArea: { silent: true, data: affected }, markLine: { silent: true, symbol: ["none", "none"], label: { formatter: copy.cutoff, color: "#8c9895" }, lineStyle: { color: "#697573", type: "dashed" }, data: [{ xAxis: scenario.data_cutoff }] } },
      ],
    };
    chart.setOption(option, true);
  }, [chart, forecast, scenario]);
  return <div ref={elementRef} className="sx-chart" role="img" aria-label={ui.scenarioLab.result.title} />;
}
