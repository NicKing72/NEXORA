"""Explainable operational completeness, exposure and priority scoring."""

from __future__ import annotations

from datetime import datetime

from nexora_api.schemas.portfolio import PortfolioOperationalInputs

CALCULATION_VERSION = "portfolio_priority_v1"
COMPONENT_WEIGHTS = {
    "forecast_magnitude": 0.30,
    "peak_concentration": 0.20,
    "forecast_variability": 0.20,
    "inventory_coverage": 0.20,
    "operational_constraint": 0.10,
}
RISK_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
CORE_OPERATIONAL_FIELDS = ("current_inventory", "inbound_inventory", "safety_stock", "lead_time")


def resolve_operational_inputs(
    inputs: PortfolioOperationalInputs,
    cutoff: datetime,
) -> tuple[dict[str, object], dict[str, float | None], list[str], list[str], str]:
    snapshot: dict[str, object] = {}
    values: dict[str, float | None] = {}
    missing: list[str] = []
    warnings: list[str] = []
    available_core = 0
    for field, _item in inputs.__fields__.items():
        value_input = getattr(inputs, field)
        status = value_input.status
        available_at = value_input.available_at or cutoff
        value = value_input.value
        if status == "available" and available_at > cutoff:
            warnings.append(f"{field}:available_after_cutoff")
            status = "missing"
            value = None
        snapshot[field] = {
            "status": status,
            "value": value,
            "available_at": available_at.isoformat(),
            "source_type": value_input.source_type,
            "source_reference": value_input.source_reference,
        }
        values[field] = float(value) if status == "available" and value is not None else None
        if field in CORE_OPERATIONAL_FIELDS:
            if status == "available":
                available_core += 1
            elif status == "missing":
                missing.append(field)
    completeness = (
        "sufficient_data"
        if available_core >= 3
        else "partial_data"
        if available_core
        else "insufficient_data"
    )
    return snapshot, values, missing, warnings, completeness


def classify_risk(
    *,
    coverage: float | None,
    horizon: int,
    current_inventory: float | None,
    safety_stock: float | None,
    lead_time: float | None,
) -> tuple[str, list[str]]:
    if coverage is None:
        return "unknown", ["inventory_coverage_unavailable"]
    ratio = coverage / max(horizon, 1)
    if ratio <= 0.25:
        risk = "critical"
        reasons = ["coverage_below_quarter_horizon"]
    elif ratio <= 0.50:
        risk = "high"
        reasons = ["coverage_below_half_horizon"]
    elif ratio < 1:
        risk = "medium"
        reasons = ["coverage_below_full_horizon"]
    else:
        risk = "low"
        reasons = ["coverage_reaches_horizon"]
    if lead_time is not None and coverage <= lead_time:
        risk = "critical"
        reasons.append("coverage_not_above_lead_time")
    if (
        safety_stock is not None
        and current_inventory is not None
        and current_inventory <= safety_stock
    ):
        if RISK_ORDER[risk] > RISK_ORDER["high"]:
            risk = "high"
        reasons.append("inventory_at_or_below_safety_stock")
    return risk, reasons


def priority_score(
    *,
    metrics: dict[str, object],
    max_forecast_total: float,
    coverage: float | None,
    horizon: int,
    current_inventory: float | None,
    safety_stock: float | None,
    lead_time: float | None,
) -> tuple[float, str, dict[str, object]]:
    average = float(metrics["forecast_average"])
    peak = float(metrics["forecast_peak"])
    total = float(metrics["forecast_total"])
    variability = metrics["forecast_variability"]
    raw: dict[str, float | None] = {
        "forecast_magnitude": total / max_forecast_total if max_forecast_total > 0 else 0.0,
        "peak_concentration": min(max((peak / average) - 1, 0.0), 1.0) if average > 0 else None,
        "forecast_variability": min(float(variability), 1.0) if variability is not None else None,
        "inventory_coverage": (
            1 - min(coverage / max(horizon, 1), 1.0) if coverage is not None else None
        ),
        "operational_constraint": None,
    }
    constraints: list[float] = []
    if current_inventory is not None and safety_stock is not None:
        constraints.append(
            1.0 if current_inventory <= safety_stock else safety_stock / current_inventory
        )
    if coverage is not None and lead_time is not None and lead_time > 0:
        constraints.append(min(lead_time / max(coverage, 1e-12), 1.0))
    if constraints:
        raw["operational_constraint"] = max(constraints)
    valid_weight = sum(COMPONENT_WEIGHTS[key] for key, value in raw.items() if value is not None)
    score = (
        100
        * sum(
            COMPONENT_WEIGHTS[key] * float(value)
            for key, value in raw.items()
            if value is not None
        )
        / valid_weight
        if valid_weight
        else 0.0
    )
    components = {
        key: {
            "available": value is not None,
            "raw_score": round(float(value) * 100, 4) if value is not None else None,
            "configured_weight": weight,
            "normalized_weight": (
                weight / valid_weight if value is not None and valid_weight else None
            ),
        }
        for key, weight in COMPONENT_WEIGHTS.items()
        for value in [raw[key]]
    }
    status = "complete" if all(value is not None for value in raw.values()) else "partial"
    return round(score, 4), status, components
