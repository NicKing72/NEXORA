"""Leakage-safe local comparable baselines for canonical demand periods."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nexora_api.services.context.impact.preparation import EvidencePoint


@dataclass(frozen=True)
class BaselineResult:
    baseline_value: float | None
    observed_value: float | None
    references: tuple[EvidencePoint, ...]
    observed: tuple[EvidencePoint, ...]
    expected_event_periods: int


def comparable_baseline(
    points: list[EvidencePoint], event: list[EvidencePoint], frequency: str
) -> BaselineResult:
    """Compare event periods only with earlier, complete canonical periods."""
    if not event:
        return BaselineResult(None, None, (), (), 0)
    event_dates = {point.period for point in event}
    candidates = [
        point
        for point in points
        if point.period < min(event_dates)
        and point.period not in event_dates
        and not point.is_partial
        and point.demand is not None
    ]
    references: list[EvidencePoint] = []
    if frequency == "daily":
        for observed in event:
            matches = [
                point
                for point in candidates
                if point.period.weekday() == observed.period.weekday()
            ][-8:]
            references.extend(matches)
    else:
        window = 8 if frequency == "weekly" else 6 if frequency == "monthly" else 8
        references = candidates[-window:]

    unique_references = tuple(
        {point.period: point for point in references}.values()
    )
    valid_observed = tuple(
        point for point in event if point.demand is not None and not point.is_partial
    )
    baseline = (
        float(np.mean([point.demand for point in unique_references]))
        if unique_references
        else None
    )
    observed_value = (
        float(np.mean([point.demand for point in valid_observed]))
        if valid_observed
        else None
    )
    return BaselineResult(
        baseline_value=baseline,
        observed_value=observed_value,
        references=unique_references,
        observed=valid_observed,
        expected_event_periods=len(event),
    )

