"""Demand trajectory preparation without recalculating Forecast Core."""

from __future__ import annotations

from nexora_api.models.dataset import ForecastRun
from nexora_api.models.scenario import ScenarioRun


def demand_points(
    forecast: ForecastRun, scenario: ScenarioRun | None
) -> tuple[str, list[dict[str, object]]]:
    if scenario is not None:
        points = [
            {"timestamp": point.timestamp.isoformat(), "demand": float(point.scenario)}
            for point in sorted(scenario.points, key=lambda item: item.timestamp)
        ]
        return "scenario", points
    points = [
        {
            "timestamp": point.timestamp.isoformat(),
            "demand": float(point.forecast),
            "lower_80": point.lower_80,
            "upper_80": point.upper_80,
            "lower_95": point.lower_95,
            "upper_95": point.upper_95,
        }
        for point in sorted(forecast.points, key=lambda item: item.timestamp)
    ]
    return "official_forecast", points


def demand_metrics(points: list[dict[str, object]]) -> dict[str, float]:
    values = [float(point["demand"]) for point in points]
    total = sum(values)
    return {
        "total": total,
        "average": total / len(values) if values else 0.0,
        "peak": max(values) if values else 0.0,
    }
