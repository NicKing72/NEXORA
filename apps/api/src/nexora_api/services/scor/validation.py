"""Mathematical and temporal safety for raw SCOR inputs."""

from __future__ import annotations

import math
from datetime import datetime

from nexora_api.services.scor.definitions import MetricDefinition


def numeric(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def validate_period(period_start: datetime, period_end: datetime, cutoff: datetime) -> None:
    if period_start >= period_end:
        raise ValueError("period_start_must_precede_period_end")
    if cutoff < period_end:
        raise ValueError("cutoff_must_not_precede_period_end")


def validate_values(
    definition: MetricDefinition, values: dict[str, object]
) -> tuple[str | None, str | None]:
    for input_definition in definition.inputs:
        value = values.get(input_definition.id)
        if value is None and input_definition.required:
            return "incomplete", f"missing_input:{input_definition.id}"
        if value is None:
            continue
        parsed = numeric(value)
        if parsed is None:
            return "invalid", f"non_numeric_input:{input_definition.id}"
        if input_definition.nonnegative and parsed < 0:
            return "invalid", f"negative_input:{input_definition.id}"
        if input_definition.direct_percentage and parsed > 100:
            return "invalid", f"percentage_out_of_range:{input_definition.id}"
    return None, None


def validate_monthly(
    definition: MetricDefinition, monthly: list[dict[str, object]]
) -> tuple[str | None, str | None]:
    if not monthly:
        return None, None
    if len(monthly) != 6:
        return "invalid", "six_complete_months_required"
    for index, month in enumerate(monthly, start=1):
        status, reason = validate_values(definition, month)
        if status:
            return status, f"month_{index}:{reason}"
    return None, None
