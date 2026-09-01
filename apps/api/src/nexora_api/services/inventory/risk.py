"""Deterministic descriptive inventory risk classification."""

from __future__ import annotations


def classify_risk(
    *,
    physical_coverage: float | None,
    lead_time_periods: float | None,
    shortage: float | None,
    surplus: float | None,
    forecast_total: float,
) -> tuple[str, list[str]]:
    if physical_coverage is None:
        return "unknown", ["insufficient_inventory_evidence"]
    if shortage is not None and shortage > 0:
        return "critical", ["projected_shortage"]
    if lead_time_periods is not None and physical_coverage < lead_time_periods:
        return "critical", ["coverage_below_lead_time"]
    if lead_time_periods is not None and physical_coverage < lead_time_periods * 1.25:
        return "high", ["coverage_near_lead_time"]
    if surplus is not None and surplus > forecast_total:
        return "medium", ["significant_projected_surplus"]
    return "low", ["no_quantified_shortage_or_excess_signal"]
