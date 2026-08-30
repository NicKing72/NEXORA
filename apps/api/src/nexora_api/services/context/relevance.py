"""Deterministic scope matching for contextual signals."""

from dataclasses import dataclass

from nexora_api.models.context import ContextSignal


@dataclass(frozen=True)
class SeriesContext:
    product: str | None = None
    category: str | None = None
    location: str | None = None
    channel: str | None = None
    market: str | None = None
    country: str | None = None
    region: str | None = None


MATCH_DIMENSIONS = ("country", "region", "product", "category", "location", "channel", "market")


def match_signal(
    signal: ContextSignal, context: SeriesContext
) -> tuple[bool, list[dict[str, str]]]:
    """Require every explicit signal dimension to match the selected series context."""
    reasons: list[dict[str, str]] = []
    for dimension in MATCH_DIMENSIONS:
        expected = getattr(signal, dimension)
        if expected is None:
            continue
        actual = getattr(context, dimension)
        if actual is None or actual.casefold() != expected.casefold():
            return False, []
        reasons.append({"dimension": dimension, "expected": expected, "actual": actual})

    if signal.scope_type == "global" and not reasons:
        reasons.append({"dimension": "scope", "expected": "global", "actual": "global"})
    return True, reasons

