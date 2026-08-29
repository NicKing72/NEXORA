"""Transparent champion selection based on out-of-sample metrics."""

from __future__ import annotations

WMAPE_TIE_TOLERANCE = 0.005
"""WMAPE proportion equivalent to 0.5 percentage points."""
STABILITY_ORDER = {"high": 0, "moderate": 1, "low": 2, "insufficient": 3}


def _secondary_key(result: dict[str, object]) -> tuple[float, float, int, str]:
    metrics = result["metrics"]
    bias = metrics.get("bias_percent")
    rmse = metrics.get("rmse")
    stability = result["stability"].get("label", "insufficient")
    return (
        abs(float(bias)) if bias is not None else float("inf"),
        float(rmse) if rmse is not None else float("inf"),
        STABILITY_ORDER.get(str(stability), 4),
        str(result["model_name"]),
    )


def rank_models(results: list[dict[str, object]]) -> tuple[list[dict[str, object]], str | None]:
    """Rank successful candidates, treating WMAPE differences under 0.5 pp as ties."""
    remaining = [
        result
        for result in results
        if result.get("status") == "succeeded" and result["metrics"].get("wmape") is not None
    ]
    ranked: list[dict[str, object]] = []
    champion_used_tie_break = False
    while remaining:
        best_wmape = min(float(item["metrics"]["wmape"]) for item in remaining)
        similar = [
            item
            for item in remaining
            if float(item["metrics"]["wmape"]) - best_wmape < WMAPE_TIE_TOLERANCE
        ]
        similar.sort(key=_secondary_key)
        if not ranked and len(similar) > 1:
            champion_used_tie_break = True
        for item in similar:
            item["rank"] = len(ranked) + 1
            ranked.append(item)
            remaining.remove(item)
    unranked = [result for result in results if result not in ranked]
    for result in unranked:
        result["rank"] = None
    reason = None
    if ranked:
        reason = "near_tie_bias_stability" if champion_used_tie_break else "lowest_wmape"
    return ranked + unranked, reason
