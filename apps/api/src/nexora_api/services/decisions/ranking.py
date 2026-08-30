"""Stable and explainable recommendation ranking."""

from __future__ import annotations

from nexora_api.services.decisions.catalog import ACTION_ORDER, PRIORITY_WEIGHT


def rank_candidates(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    action_index = {action: index for index, action in enumerate(ACTION_ORDER)}
    return sorted(
        candidates,
        key=lambda item: (
            -PRIORITY_WEIGHT[str(item["priority"])],
            -float(item["support_score"]),
            action_index.get(str(item["action_type"]), len(action_index)),
            str(item["stable_key"]),
        ),
    )


def evidence_level(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.6:
        return "moderate"
    if score >= 0.35:
        return "low"
    return "insufficient"
