"""Stable ranking that preserves mathematical ties."""

from __future__ import annotations

from nexora_api.services.portfolio.risk import RISK_ORDER


def rank_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    ordered = sorted(
        items,
        key=lambda item: (
            RISK_ORDER[str(item["risk_level"])],
            -float(item["priority_score"]),
            -float(item["forecast_total"]),
            str(item["series_key"]),
        ),
    )
    previous: tuple[int, float, float] | None = None
    rank = 0
    for position, item in enumerate(ordered, start=1):
        comparison = (
            RISK_ORDER[str(item["risk_level"])],
            round(float(item["priority_score"]), 8),
            round(float(item["forecast_total"]), 8),
        )
        if comparison != previous:
            rank = position
            previous = comparison
        item["rank"] = rank
    return ordered
