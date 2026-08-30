"""NEXORA Gap Score: explicit target evaluation, never an official SCOR score."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GapEvaluation:
    score: float | None
    status: str
    explanation: str


def gap_score(
    value: float,
    *,
    direction: str,
    target: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> GapEvaluation:
    if direction == "higher_is_better":
        if target is None or target <= 0:
            return GapEvaluation(None, "invalid_target", "higher_is_better requiere target > 0")
        score = max(0.0, (target - value) / abs(target) * 100)
        formula = f"max(0, ({target:g} - {value:g}) / |{target:g}| × 100)"
    elif direction == "lower_is_better":
        if target is None or target < 0:
            return GapEvaluation(None, "invalid_target", "lower_is_better requiere target >= 0")
        if target == 0:
            score = 0.0 if value <= 0 else 100.0
            formula = "0 si valor <= 0; de otro modo 100 (target cero)"
        else:
            score = max(0.0, (value - target) / abs(target) * 100)
            formula = f"max(0, ({value:g} - {target:g}) / |{target:g}| × 100)"
    elif direction == "target_range":
        if minimum is None or maximum is None or maximum <= minimum:
            return GapEvaluation(None, "invalid_target", "target_range requiere min < max")
        width = maximum - minimum
        if value < minimum:
            score = (minimum - value) / width * 100
        elif value > maximum:
            score = (value - maximum) / width * 100
        else:
            score = 0.0
        formula = f"distancia de {value:g} al rango [{minimum:g}, {maximum:g}] / {width:g} × 100"
    else:
        return GapEvaluation(None, "invalid_target", "dirección de target no compatible")
    return GapEvaluation(round(min(100.0, score), 4), "evaluated", formula)
