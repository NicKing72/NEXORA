"""Deterministic KPI calculation with reconstructable formulas."""

from __future__ import annotations

from dataclasses import dataclass, field

from nexora_api.services.scor.definitions import BY_ID, MetricDefinition
from nexora_api.services.scor.validation import numeric, validate_monthly, validate_values


@dataclass
class Calculation:
    metric_id: str
    process: str
    attribute: str
    method: str
    formula: str
    substituted_formula: str
    inputs: dict[str, object]
    unit: str
    evidence_status: str
    result: float | None = None
    numerator: float | None = None
    denominator: float | None = None
    ratio_decimal: float | None = None
    reason: str | None = None
    details: dict[str, object] = field(default_factory=dict)


def aggregate_monthly_ratio(
    monthly: list[dict[str, object]], numerator_key: str, denominator_key: str
) -> tuple[float, float]:
    """Required semestral rule: ratio of sums, never mean of monthly ratios."""
    return (
        sum(float(month[numerator_key]) for month in monthly),
        sum(float(month[denominator_key]) for month in monthly),
    )


def _empty(
    definition: MetricDefinition, status: str, reason: str, values: dict[str, object]
) -> Calculation:
    return Calculation(
        definition.id,
        definition.process,
        definition.attribute,
        definition.method,
        definition.formula,
        "",
        values,
        definition.unit,
        status,
        reason=reason,
    )


def calculate_metric(
    metric_id: str,
    values: dict[str, object],
    *,
    monthly_values: list[dict[str, object]] | None = None,
    metadata: dict[str, object] | None = None,
    dependencies: dict[str, Calculation] | None = None,
    not_applicable: bool = False,
) -> Calculation:
    definition = BY_ID[metric_id]
    metadata = metadata or {}
    monthly = monthly_values or []
    if not_applicable:
        return _empty(definition, "not_applicable", "declared_not_applicable", values)
    if definition.method == "dependent_product":
        return _dependent_product(definition, dependencies or {})
    status, reason = validate_monthly(definition, monthly)
    if not status and not monthly:
        status, reason = validate_values(definition, values)
    if status:
        return _empty(definition, status, reason or status, {"values": values, "monthly": monthly})
    resolved = dict(values)
    if monthly and definition.numerator_key and definition.denominator_key:
        numerator, denominator = aggregate_monthly_ratio(
            monthly, definition.numerator_key, definition.denominator_key
        )
        resolved[definition.numerator_key] = numerator
        resolved[definition.denominator_key] = denominator
    if definition.method == "ratio_of_sums":
        return _ratio(definition, resolved, monthly, metadata)
    if definition.method == "sum_subtract":
        receivable = float(resolved["days_receivable"])
        inventory = float(resolved["inventory_days"])
        payable = float(resolved["days_payable"])
        result = receivable + inventory - payable
        return Calculation(
            definition.id,
            definition.process,
            definition.attribute,
            definition.method,
            definition.formula,
            f"{receivable:g} + {inventory:g} - {payable:g} = {result:g}",
            resolved,
            definition.unit,
            "complete",
            result=result,
        )
    if definition.method == "direct":
        key = definition.inputs[0].id
        result = float(resolved[key])
        return Calculation(
            definition.id,
            definition.process,
            definition.attribute,
            definition.method,
            definition.formula,
            f"{key} = {result:g}%",
            resolved,
            definition.unit,
            "complete",
            result=result,
            ratio_decimal=result / 100,
        )
    if definition.method == "rofa":
        return _rofa(definition, resolved)
    if definition.method == "exclusive_choice":
        return _ofct(definition, resolved, metadata)
    return _empty(definition, "invalid", "unsupported_method", resolved)


def _ratio(
    definition: MetricDefinition,
    values: dict[str, object],
    monthly: list[dict[str, object]],
    metadata: dict[str, object],
) -> Calculation:
    assert definition.numerator_key and definition.denominator_key
    numerator = float(values[definition.numerator_key])
    denominator = float(values[definition.denominator_key])
    unit = definition.unit
    if unit == "time_unit":
        unit = str(metadata.get("time_unit") or "")
        if unit not in {"minutos", "horas"}:
            return _empty(definition, "invalid", "incompatible_or_missing_time_unit", values)
    if unit == "currency/unit":
        currency = str(metadata.get("currency") or "")
        if not currency:
            return _empty(definition, "incomplete", "missing_currency", values)
        unit = f"{currency} / unidad"
    if denominator == 0:
        result = _empty(definition, "insufficient_evidence", "denominator_zero", values)
        result.numerator, result.denominator = numerator, denominator
        return result
    ratio_decimal = numerator / denominator
    result_value = ratio_decimal * definition.factor
    details = {"aggregation": "ratio_of_sums" if monthly else "period_accumulated_inputs"}
    return Calculation(
        definition.id,
        definition.process,
        definition.attribute,
        definition.method,
        definition.formula,
        f"({numerator:g} / {denominator:g}) × {definition.factor:g} = {result_value:.6g}",
        {"values": values, "monthly": monthly},
        unit,
        "complete",
        result=result_value,
        numerator=numerator,
        denominator=denominator,
        ratio_decimal=ratio_decimal if definition.factor == 100 else None,
        details=details,
    )


def _rofa(definition: MetricDefinition, values: dict[str, object]) -> Calculation:
    revenue = float(values["supply_chain_revenue_6m"])
    cost = float(values["total_supply_chain_cost_6m"])
    assets = float(values["logistics_fixed_assets_value"])
    benefit = revenue - cost
    if assets == 0:
        result = _empty(definition, "insufficient_evidence", "denominator_zero", values)
        result.numerator, result.denominator = benefit, assets
        return result
    ratio_decimal = benefit / assets
    percentage = ratio_decimal * 100
    return Calculation(
        definition.id,
        definition.process,
        definition.attribute,
        definition.method,
        definition.formula,
        f"(({revenue:g} - {cost:g}) / {assets:g}) × 100 = {percentage:.6g}",
        values,
        "%",
        "complete",
        result=percentage,
        numerator=benefit,
        denominator=assets,
        ratio_decimal=ratio_decimal,
        details={"benefit": benefit, "assets": assets},
    )


def _dependent_product(
    definition: MetricDefinition, dependencies: dict[str, Calculation]
) -> Calculation:
    component_ids = ("D01", "D02", "D03", "D04")
    components = [dependencies.get(metric_id) for metric_id in component_ids]
    if any(item is None or item.evidence_status != "complete" for item in components):
        return _empty(
            definition,
            "incomplete",
            "missing_complete_pof_component",
            {"component_ids": list(component_ids)},
        )
    decimals = [float(item.result) / 100 for item in components if item and item.result is not None]
    result = decimals[0] * decimals[1] * decimals[2] * decimals[3] * 100
    expression = " × ".join(f"{value:.6g}" for value in decimals)
    return Calculation(
        definition.id,
        definition.process,
        definition.attribute,
        definition.method,
        definition.formula,
        f"({expression}) × 100 = {result:.6g}",
        {metric_id: dependencies[metric_id].result for metric_id in component_ids},
        "%",
        "complete",
        result=result,
        ratio_decimal=result / 100,
        details={"components": list(component_ids), "method": "product_not_average"},
    )


def _ofct(
    definition: MetricDefinition, values: dict[str, object], metadata: dict[str, object]
) -> Calculation:
    unit = str(metadata.get("time_unit") or "")
    if unit not in {"horas", "días"}:
        return _empty(definition, "invalid", "incompatible_or_missing_time_unit", values)
    observed = numeric(values.get("observed_total"))
    component_keys = ("order_lead_time", "make_time", "delivery_time")
    components = [numeric(values.get(key)) for key in component_keys]
    has_components = all(value is not None for value in components)
    if observed is not None and has_components:
        return _empty(
            definition, "invalid", "observed_and_components_are_mutually_exclusive", values
        )
    if observed is not None:
        if observed < 0:
            return _empty(definition, "invalid", "negative_input:observed_total", values)
        return Calculation(
            definition.id,
            definition.process,
            definition.attribute,
            "observed_total",
            definition.formula,
            f"Tiempo total observado = {observed:g}",
            values,
            unit,
            "complete",
            result=observed,
        )
    if has_components:
        assert all(value is not None for value in components)
        if any(float(value) < 0 for value in components):
            return _empty(definition, "invalid", "negative_component", values)
        result = sum(float(value) for value in components)
        return Calculation(
            definition.id,
            definition.process,
            definition.attribute,
            "component_sum",
            definition.formula,
            f"{components[0]:g} + {components[1]:g} + {components[2]:g} = {result:g}",
            values,
            unit,
            "complete",
            result=result,
        )
    return _empty(definition, "incomplete", "missing_observed_total_or_components", values)
