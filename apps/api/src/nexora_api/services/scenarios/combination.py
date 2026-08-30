"""Ordered combination of assumptions and overlap auditing."""

from __future__ import annotations

from datetime import UTC, datetime, time

from nexora_api.models.scenario import ScenarioAssumption
from nexora_api.services.scenarios.transforms import apply_transform


def _instant(date_text: str) -> datetime:
    return datetime.combine(datetime.fromisoformat(date_text).date(), time.min, UTC)


def is_active(assumption: ScenarioAssumption, timestamp: datetime) -> bool:
    end = assumption.end_at or assumption.start_at
    return assumption.start_at <= timestamp <= end


def combine(
    baseline_points: list[dict[str, object]], assumptions: list[ScenarioAssumption]
) -> tuple[list[dict[str, object]], list[str]]:
    ordered = sorted(assumptions, key=lambda item: (item.order_index, item.id))
    output: list[dict[str, object]] = []
    warnings: set[str] = set()
    for point in baseline_points:
        timestamp = _instant(str(point["timestamp"]))
        baseline = float(point["forecast"])
        value = baseline
        active = [item for item in ordered if is_active(item, timestamp)]
        if len(active) > 1:
            warnings.add("overlapping_assumptions_applied_in_declared_order")
        if sum(item.application_method == "sales_capacity_cap" for item in active) > 1:
            warnings.add("overlapping_supply_restrictions")
        point_warnings: set[str] = set()
        for assumption in active:
            result = apply_transform(
                value, baseline, assumption.application_method, float(assumption.magnitude or 0)
            )
            value = result.value
            point_warnings.update(result.warnings)
        warnings.update(point_warnings)
        delta = value - baseline
        output.append(
            {
                "timestamp": str(point["timestamp"]),
                "baseline": round(baseline, 6),
                "scenario": round(value, 6),
                "absolute_delta": round(delta, 6),
                "relative_delta": round(delta / baseline, 6) if baseline != 0 else None,
                "lower_80": point.get("lower_80"),
                "upper_80": point.get("upper_80"),
                "lower_95": point.get("lower_95"),
                "upper_95": point.get("upper_95"),
                "active_assumption_ids": [item.id for item in active],
            }
        )
    return output, sorted(warnings)
