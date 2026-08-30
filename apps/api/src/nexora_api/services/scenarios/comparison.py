"""Explainable baseline-versus-scenario summary calculations."""

from __future__ import annotations


def summarize(points: list[dict[str, object]], assumption_count: int) -> dict[str, object]:
    baseline_total = sum(float(point["baseline"]) for point in points)
    scenario_total = sum(float(point["scenario"]) for point in points)
    delta = scenario_total - baseline_total
    affected = [point for point in points if point["active_assumption_ids"]]
    return {
        "baseline_total": round(baseline_total, 6),
        "scenario_total": round(scenario_total, 6),
        "absolute_delta": round(delta, 6),
        "relative_delta": round(delta / baseline_total, 6) if baseline_total != 0 else None,
        "max_period_change": round(
            max((abs(float(point["absolute_delta"])) for point in points), default=0.0), 6
        ),
        "affected_periods": len(affected),
        "assumption_count": assumption_count,
    }
