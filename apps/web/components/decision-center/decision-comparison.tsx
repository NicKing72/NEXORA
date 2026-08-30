"use client";

import type { ECharts, EChartsOption } from "echarts";
import { useEffect, useRef, useState } from "react";

import type { DecisionRun } from "@/lib/decision-types";
import { ui } from "@/lib/i18n";

function format(value: number | null | undefined) {
  return value == null ? "—" : new Intl.NumberFormat("es-PE", { maximumFractionDigits: 1 }).format(value);
}

export function DecisionComparison({ run }: Readonly<{ run: DecisionRun }>) {
  const elementRef = useRef<HTMLDivElement>(null);
  const [chart, setChart] = useState<ECharts | null>(null);
  const scenario = run.source_snapshot.scenario;
  useEffect(() => {
    if (!elementRef.current || !scenario) return;
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
  }, [scenario]);
  useEffect(() => {
    if (!chart || !scenario) return;
    const copy = ui.decisionCenter.comparison;
    const option: EChartsOption = {
      animationDuration: 380,
      backgroundColor: "transparent",
      grid: { left: 52, right: 24, top: 42, bottom: 48 },
      legend: { top: 2, right: 2, textStyle: { color: "#a4afad" } },
      tooltip: { trigger: "axis", backgroundColor: "rgba(13,17,18,.98)", borderColor: "#2a3535", textStyle: { color: "#f0f3f1" } },
      xAxis: { type: "time", axisLabel: { color: "#7f8b89" }, axisLine: { lineStyle: { color: "#2a3334" } } },
      yAxis: { type: "value", axisLabel: { color: "#7f8b89" }, splitLine: { lineStyle: { color: "rgba(75,89,87,.18)" } } },
      series: [
        { name: copy.baseline, type: "line", data: scenario.points.map((point) => [point.timestamp, point.baseline]), symbol: "none", lineStyle: { color: "#8cc6bd", type: "dashed", width: 2 } },
        { name: copy.scenario, type: "line", data: scenario.points.map((point) => [point.timestamp, point.scenario]), symbol: "circle", symbolSize: 4, lineStyle: { color: "#d8ab73", width: 2.3 } },
      ],
    };
    chart.setOption(option, true);
  }, [chart, scenario]);
  if (!scenario) return null;
  const summary = scenario.summary;
  return <section className="dc-panel dc-comparison"><div className="dc-heading"><div><span>{ui.decisionCenter.comparison.index}</span><h2>{ui.decisionCenter.comparison.title}</h2></div><strong>HIPOTÉTICO</strong></div><div className="dc-comparison-metrics"><div><span>{ui.decisionCenter.comparison.baseline}</span><b>{format(summary.baseline_total)}</b></div><div><span>{ui.decisionCenter.comparison.scenario}</span><b>{format(summary.scenario_total)}</b></div><div><span>{ui.decisionCenter.comparison.delta}</span><b>{summary.relative_delta == null ? "—" : `${summary.relative_delta >= 0 ? "+" : ""}${(summary.relative_delta * 100).toFixed(1)}%`}</b></div><div><span>{ui.decisionCenter.comparison.affected}</span><b>{format(summary.affected_periods)}</b></div></div><div ref={elementRef} className="dc-chart" role="img" aria-label={ui.decisionCenter.comparison.title} /><p>{ui.decisionCenter.comparison.boundary}</p></section>;
}
