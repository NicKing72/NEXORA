"""Explainable evidence score for contextual association estimates."""

from __future__ import annotations


def evidence_score(
    *,
    reference_periods: int,
    valid_event_periods: int,
    expected_event_periods: int,
    contaminated_periods: int,
    comparable_events: int,
    confidence: float | None,
) -> tuple[float, str, dict[str, object]]:
    total_periods = max(1, reference_periods + valid_event_periods)
    components = {
        "reference_volume": 25.0 * min(reference_periods / 8.0, 1.0),
        "event_coverage": 25.0
        * min(valid_event_periods / max(1, expected_event_periods), 1.0),
        "data_quality": 20.0
        * max(0.0, 1.0 - contaminated_periods / total_periods),
        "comparable_events": 15.0 * min(comparable_events / 3.0, 1.0),
        "provenance_confidence": 15.0 * (confidence if confidence is not None else 0.5),
    }
    rounded = {key: round(value, 2) for key, value in components.items()}
    score = round(sum(rounded.values()), 2)
    if score >= 80:
        level = "high"
    elif score >= 60:
        level = "moderate"
    elif score >= 40:
        level = "low"
    else:
        level = "insufficient"
    return score, level, {
        "formula_version": "context_evidence_v1",
        "weights": {
            "reference_volume": 25,
            "event_coverage": 25,
            "data_quality": 20,
            "comparable_events": 15,
            "provenance_confidence": 15,
        },
        "components": rounded,
    }

