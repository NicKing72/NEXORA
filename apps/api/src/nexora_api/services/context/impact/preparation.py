"""Prepare canonical Series Engine output for contextual evidence analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class EvidencePoint:
    period: date
    demand: float | None
    is_partial: bool
    events: dict[str, int]
    coverage_ratio: float


def parse_points(profile: dict[str, object], cutoff: date) -> list[EvidencePoint]:
    points: list[EvidencePoint] = []
    for raw in profile["points"]:  # type: ignore[index]
        point = raw  # type: ignore[assignment]
        period = date.fromisoformat(str(point["date"])[:10])
        if period > cutoff:
            continue
        demand = point["demand"]
        points.append(
            EvidencePoint(
                period=period,
                demand=float(demand) if demand is not None else None,
                is_partial=bool(point["is_partial"]),
                events={key: int(value) for key, value in point["events"].items()},
                coverage_ratio=float(point["coverage_ratio"]),
            )
        )
    return points


def period_end(period: date, frequency: str) -> date:
    if frequency == "daily":
        return period
    if frequency == "weekly":
        return period + timedelta(days=6)
    if frequency == "monthly":
        if period.month == 12:
            return date(period.year + 1, 1, 1) - timedelta(days=1)
        return date(period.year, period.month + 1, 1) - timedelta(days=1)
    return period


def event_points(
    points: list[EvidencePoint], event_start: datetime, event_end: datetime | None, frequency: str
) -> list[EvidencePoint]:
    start = event_start.date()
    end = (event_end or event_start).date()
    return [
        point
        for point in points
        if point.period <= end and period_end(point.period, frequency) >= start
    ]

