"""Pure deterministic transformations applied to copied baseline values."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransformResult:
    value: float
    warnings: tuple[str, ...] = ()


def apply_transform(
    current: float, baseline: float, method: str, magnitude: float
) -> TransformResult:
    if method == "multiplicative":
        candidate = current * (1.0 + magnitude)
    elif method == "additive":
        candidate = current + magnitude
    elif method == "sales_capacity_cap":
        candidate = min(current, baseline * magnitude)
        return TransformResult(max(0.0, candidate), ("sales_potentially_censored",))
    else:
        raise ValueError(f"Unsupported scenario method: {method}")
    if candidate < 0:
        return TransformResult(0.0, ("negative_result_clamped_to_zero",))
    return TransformResult(candidate)
