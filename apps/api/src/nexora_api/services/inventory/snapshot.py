"""Frozen source and operational input snapshots."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from nexora_api.models.dataset import ForecastRun
from nexora_api.models.decision import DecisionRun
from nexora_api.models.portfolio import PortfolioRun
from nexora_api.models.scenario import ScenarioRun
from nexora_api.schemas.inventory import InventoryOperationalInputs


def resolve_inputs(
    inputs: InventoryOperationalInputs, cutoff: datetime
) -> tuple[dict[str, object], dict[str, float | None], list[str], list[str]]:
    snapshot: dict[str, object] = {}
    values: dict[str, float | None] = {}
    missing: list[str] = []
    warnings: list[str] = []
    for name, item in inputs.__dict__.items():
        status = item.status
        available_at = item.available_at or cutoff
        value = item.value
        if status == "available" and available_at > cutoff:
            status, value = "missing", None
            warnings.append(f"{name}:available_after_cutoff")
        if status == "missing":
            missing.append(name)
        values[name] = float(value) if value is not None and status == "available" else None
        snapshot[name] = {
            "value": values[name],
            "status": status,
            "unit": item.unit,
            "source_type": item.source_type,
            "source_reference": item.source_reference,
            "available_at": available_at.isoformat(),
        }
    return snapshot, values, missing, warnings


def freeze_sources(
    forecast: ForecastRun,
    scenario: ScenarioRun | None,
    portfolio: PortfolioRun | None,
    decision: DecisionRun | None,
    demand_points: list[dict[str, object]],
) -> dict[str, object]:
    encoded = json.dumps(demand_points, sort_keys=True, separators=(",", ":")).encode()
    return {
        "forecast": {
            "id": forecast.id,
            "dataset_id": forecast.dataset_id,
            "created_at": forecast.created_at.isoformat(),
            "data_cutoff": forecast.data_cutoff.isoformat(),
            "frequency": forecast.frequency,
            "horizon": forecast.requested_horizon,
            "champion": forecast.champion_model,
            "product": forecast.product,
            "location": forecast.location,
            "category": forecast.category,
        },
        "scenario": None
        if scenario is None
        else {
            "id": scenario.id,
            "forecast_run_id": scenario.forecast_run_id,
            "executed_at": scenario.executed_at.isoformat() if scenario.executed_at else None,
            "status": scenario.status,
        },
        "portfolio": None
        if portfolio is None
        else {
            "id": portfolio.id,
            "created_at": portfolio.created_at.isoformat(),
            "available_at": portfolio.available_at.isoformat(),
        },
        "decision": None
        if decision is None
        else {
            "id": decision.id,
            "created_at": decision.created_at.isoformat(),
            "decision_cutoff": decision.decision_cutoff.isoformat(),
        },
        "demand_points": demand_points,
        "demand_points_sha256": hashlib.sha256(encoded).hexdigest(),
        "sources_recalculated": False,
    }
