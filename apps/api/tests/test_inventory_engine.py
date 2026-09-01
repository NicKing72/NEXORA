"""Deterministic Inventory Engine mathematics, safety and persistence."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from nexora_api.schemas.inventory import InventoryOperationalInputs, InventoryValueInput
from nexora_api.services.inventory.coverage import coverage_views
from nexora_api.services.inventory.eoq import calculate_eoq
from nexora_api.services.inventory.reorder import (
    compatible_lead_time,
    demand_during_lead_time,
    reorder_point,
)
from nexora_api.services.inventory.replenishment import calculate_replenishment
from nexora_api.services.inventory.risk import classify_risk
from nexora_api.services.inventory.safety_stock import calculate_safety_stock
from nexora_api.services.inventory.snapshot import resolve_inputs


def _forecast(client: TestClient) -> dict:
    start = date(2024, 1, 1)
    rows = ["date,product,category,location,demand,stock"]
    for index in range(100):
        rows.append(f"{start + timedelta(days=index)},NX-I01,Core,Lima,{20 + index % 7},50")
    dataset = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("inventory.csv", ("\n".join(rows) + "\n").encode(), "text/csv")},
    ).json()
    client.post(f"/api/v1/datasets/{dataset['id']}/validate")
    client.post(f"/api/v1/datasets/{dataset['id']}/ready")
    response = client.post(
        "/api/v1/forecast-runs",
        json={
            "dataset_id": dataset["id"],
            "product": "NX-I01",
            "category": "Core",
            "location": "Lima",
            "frequency": "daily",
            "horizon": 14,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _payload(forecast: dict) -> dict:
    cutoff = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()

    def available(value: float, unit: str) -> dict[str, object]:
        return {
            "value": value,
            "status": "available",
            "unit": unit,
            "available_at": cutoff,
            "source_type": "manual",
            "source_reference": "test",
        }

    return {
        "forecast_run_id": forecast["id"],
        "cutoff": cutoff,
        "include_in_transit": True,
        "operational_inputs": {
            "inventory_on_hand": available(100, "units"),
            "inventory_in_transit": available(25, "units"),
            "lead_time": available(3, "days"),
            "safety_stock": available(20, "units"),
            "order_cost": available(40, "currency/order"),
            "holding_cost": available(4, "currency/unit/year"),
            "moq": available(50, "units"),
            "lot_multiple": available(10, "units"),
        },
    }


def test_coverage_keeps_physical_and_transit_views_separate() -> None:
    assert coverage_views(100, 50, 25) == (4, 6)
    assert coverage_views(None, 50, 25) == (None, None)


def test_missing_inventory_is_not_converted_to_zero() -> None:
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    snapshot, values, missing, _ = resolve_inputs(InventoryOperationalInputs(), cutoff)
    assert values["inventory_on_hand"] is None
    assert snapshot["inventory_on_hand"]["value"] is None
    assert "inventory_on_hand" in missing


def test_zero_is_preserved_as_declared_value() -> None:
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    inputs = InventoryOperationalInputs(
        inventory_on_hand=InventoryValueInput(value=0, status="available")
    )
    _, values, missing, _ = resolve_inputs(inputs, cutoff)
    assert values["inventory_on_hand"] == 0
    assert "inventory_on_hand" not in missing


def test_input_after_cutoff_is_excluded() -> None:
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    inputs = InventoryOperationalInputs(
        inventory_on_hand=InventoryValueInput(
            value=10, status="available", available_at=cutoff + timedelta(seconds=1)
        )
    )
    _, values, missing, warnings = resolve_inputs(inputs, cutoff)
    assert values["inventory_on_hand"] is None
    assert "inventory_on_hand" in missing
    assert warnings == ["inventory_on_hand:available_after_cutoff"]


def test_lead_time_requires_exact_frequency_unit() -> None:
    assert compatible_lead_time("daily", 3, "days") == 3
    assert compatible_lead_time("weekly", 3, "days") is None
    assert compatible_lead_time("monthly", 2, "months") == 2


def test_fractional_lead_time_demand_is_explicit() -> None:
    assert demand_during_lead_time([10, 20, 30], 1.5) == 20
    assert demand_during_lead_time([10], 2) is None


def test_declared_inputs_form_reorder_point() -> None:
    assert reorder_point(75, 20) == 95
    assert reorder_point(75, None) is None


def test_calculated_safety_stock_uses_documented_z_score() -> None:
    result, evidence = calculate_safety_stock(
        service_level=0.95, sigma_period=10, lead_time_periods=4
    )
    assert result == pytest.approx(32.898)
    assert evidence["z_score"] == 1.6449


def test_safety_stock_does_not_invent_service_level() -> None:
    result, evidence = calculate_safety_stock(
        service_level=None, sigma_period=10, lead_time_periods=4
    )
    assert result is None
    assert evidence["status"] == "not_calculable"


def test_eoq_annualization_is_explicit() -> None:
    result, evidence, holding = calculate_eoq(
        average_demand=10,
        frequency="weekly",
        order_cost=25,
        holding_cost=5,
        holding_rate=None,
        unit_cost=None,
    )
    assert result == pytest.approx((2 * 520 * 25 / 5) ** 0.5)
    assert evidence["annualization_factor"] == 52
    assert holding == 5


def test_eoq_can_derive_holding_cost_only_from_declared_rate_and_cost() -> None:
    result, evidence, holding = calculate_eoq(
        average_demand=10,
        frequency="monthly",
        order_cost=25,
        holding_cost=None,
        holding_rate=0.2,
        unit_cost=10,
    )
    assert result is not None
    assert holding == 2
    assert evidence["holding_cost_source"] == "holding_rate_times_unit_cost"


def test_eoq_missing_costs_remains_not_calculable() -> None:
    result, evidence, _ = calculate_eoq(
        average_demand=10,
        frequency="daily",
        order_cost=None,
        holding_cost=None,
        holding_rate=None,
        unit_cost=None,
    )
    assert result is None
    assert evidence["status"] == "not_calculable"


def test_replenishment_applies_moq_lot_multiple_and_capacity_in_order() -> None:
    result = calculate_replenishment(
        forecast_total=100,
        on_hand=50,
        eligible_transit=None,
        safety_stock=10,
        committed=0,
        backorders=0,
        moq=80,
        lot_multiple=25,
        capacity=90,
    )
    assert result["raw_requirement"] == 60
    assert result["recommended_quantity"] == 90
    assert [item["type"] for item in result["constraints"]] == ["moq", "lot_multiple", "capacity"]


def test_replenishment_missing_critical_inputs_requires_manual_review() -> None:
    result = calculate_replenishment(
        forecast_total=100,
        on_hand=None,
        eligible_transit=None,
        safety_stock=None,
        committed=None,
        backorders=None,
        moq=None,
        lot_multiple=None,
        capacity=None,
    )
    assert result["recommended_quantity"] is None
    assert result["projected_inventory"] is None


@pytest.mark.parametrize(
    ("coverage", "lead", "shortage", "surplus", "expected"),
    [
        (1, 2, 10, 0, "critical"),
        (2.2, 2, 0, 0, "high"),
        (8, 2, 0, 200, "medium"),
        (8, 2, 0, 0, "low"),
        (None, 2, None, None, "unknown"),
    ],
)
def test_risk_rules_are_deterministic(coverage, lead, shortage, surplus, expected) -> None:
    assert (
        classify_risk(
            physical_coverage=coverage,
            lead_time_periods=lead,
            shortage=shortage,
            surplus=surplus,
            forecast_total=100,
        )[0]
        == expected
    )


def test_api_preflight_create_recover_and_preserve_forecast(client: TestClient) -> None:
    forecast = _forecast(client)
    points_before = client.get(f"/api/v1/forecast-runs/{forecast['id']}/points").json()
    payload = _payload(forecast)
    preflight = client.post("/api/v1/inventory/preflight", json=payload)
    assert preflight.status_code == 200, preflight.text
    assert preflight.json()["calculable"]["reorder_point"] is True
    created = client.post("/api/v1/inventory", json=payload)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["forecast_run_id"] == forecast["id"]
    assert body["items"][0]["recommended_quantity"] is not None
    assert body["provenance"]["forecast_modified"] is False
    assert client.get(f"/api/v1/inventory/{body['id']}").json() == body
    assert client.get(f"/api/v1/inventory/{body['id']}/items").status_code == 200
    assert client.get(f"/api/v1/inventory/{body['id']}/summary").status_code == 200
    assert client.get(f"/api/v1/inventory/{body['id']}/evidence").status_code == 200
    assert client.get(f"/api/v1/forecast-runs/{forecast['id']}/points").json() == points_before


def test_exact_unknown_forecast_has_no_fallback(client: TestClient) -> None:
    forecast = _forecast(client)
    payload = _payload(forecast)
    payload["forecast_run_id"] = str(uuid4())
    response = client.post("/api/v1/inventory/preflight", json=payload)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "inventory_forecast_not_found"


def test_forecast_after_cutoff_is_rejected(client: TestClient) -> None:
    forecast = _forecast(client)
    payload = _payload(forecast)
    payload["cutoff"] = "2020-01-01T00:00:00Z"
    response = client.post("/api/v1/inventory/preflight", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "inventory_forecast_unavailable"


def test_demo_is_deterministic_decoupled_and_covers_expected_cases(client: TestClient) -> None:
    forecasts_before = client.get("/api/v1/forecast-runs").json()
    first = client.post("/api/v1/inventory/demo/regenerate")
    second = client.post("/api/v1/inventory/demo/regenerate")
    assert first.status_code == second.status_code == 200
    first_body, second_body = first.json(), second.json()
    assert first_body["id"] == second_body["id"]
    assert first_body["source_mode"] == "demo"
    assert len(first_body["items"]) == 8
    assert first_body["summary"] == second_body["summary"]
    assert {item["risk_level"] for item in first_body["items"]} >= {"critical", "low", "unknown"}
    assert any(item["eoq"] is not None for item in first_body["items"])
    assert any(item["eoq"] is None for item in first_body["items"])
    assert any(item["safety_stock_source"] == "declared" for item in first_body["items"])
    assert any(item["safety_stock_source"] == "calculated" for item in first_body["items"])
    assert any(item["recommended_quantity"] is None for item in first_body["items"])
    assert client.get("/api/v1/forecast-runs").json() == forecasts_before


def test_definitions_history_and_health(client: TestClient) -> None:
    assert client.get("/api/v1/inventory/definitions").status_code == 200
    client.post("/api/v1/inventory/demo/regenerate")
    assert (
        client.get("/api/v1/inventory").json()[0]["calculation_version"]
        == "inventory_replenishment_v1"
    )
    assert client.get("/health").status_code == 200
