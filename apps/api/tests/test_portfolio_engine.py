"""Deterministic Portfolio Engine metrics, selection, persistence and API."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from nexora_api.schemas.portfolio import OperationalValueInput, PortfolioOperationalInputs
from nexora_api.services.portfolio.metrics import (
    forecast_metrics,
    inventory_coverage,
    projected_exposure,
)
from nexora_api.services.portfolio.ranking import rank_items
from nexora_api.services.portfolio.risk import priority_score, resolve_operational_inputs


def _forecast(
    client: TestClient,
    *,
    frequency: str = "daily",
    horizon: int = 7,
    product: str = "A",
) -> dict:
    start = date(2024, 1, 1)
    rows = ["date,product,category,location,demand,stock"]
    count = 370 if frequency == "weekly" else 75
    for index in range(count):
        demand = 20 + index % 7
        rows.append(f"{start + timedelta(days=index)},{product},Core,North,{demand},50")
    dataset = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("portfolio.csv", ("\n".join(rows) + "\n").encode(), "text/csv")},
    ).json()
    client.post(f"/api/v1/datasets/{dataset['id']}/validate")
    client.post(f"/api/v1/datasets/{dataset['id']}/ready")
    response = client.post(
        "/api/v1/forecast-runs",
        json={
            "dataset_id": dataset["id"],
            "product": product,
            "category": "Core",
            "location": "North",
            "frequency": frequency,
            "horizon": horizon,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _request(forecast: dict, *, inventory: float | None = 100.0) -> dict:
    cutoff = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    operational = {}
    if inventory is not None:
        operational = {
            forecast["id"]: {
                "current_inventory": {
                    "value": inventory,
                    "status": "available",
                    "available_at": cutoff,
                    "source_type": "manual",
                }
            }
        }
    return {
        "dataset_id": forecast["dataset_id"],
        "forecast_run_ids": [forecast["id"]],
        "cutoff": cutoff,
        "operational_inputs": operational,
    }


def test_forecast_metrics_are_exact_and_deterministic() -> None:
    points = [
        {"forecast": 10.0, "lower_80": 8.0, "upper_80": 12.0},
        {"forecast": 20.0, "lower_80": 18.0, "upper_80": 22.0},
        {"forecast": 30.0, "lower_80": 28.0, "upper_80": 32.0},
    ]
    first = forecast_metrics(points)
    second = forecast_metrics(points)
    assert first == second
    assert first["forecast_total"] == 60
    assert first["forecast_average"] == 20
    assert first["forecast_peak"] == 30
    assert first["forecast_minimum"] == 10
    assert first["forecast_variability"] == pytest.approx(0.408248290463863)
    assert first["interval_information"]["80"]["average_width"] == 4


def test_coverage_requires_inventory_and_positive_average() -> None:
    assert inventory_coverage(60, 20) == (3, "calculated")
    assert inventory_coverage(None, 20) == (None, "not_calculable_missing_inventory")
    assert inventory_coverage(60, 0) == (
        None,
        "not_calculable_non_positive_forecast",
    )
    assert projected_exposure(100, 20, 30) == 50
    assert projected_exposure(100, 20, None) is None


def test_missing_not_applicable_and_zero_remain_distinct() -> None:
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    inputs = PortfolioOperationalInputs(
        current_inventory=OperationalValueInput(value=0, status="available"),
        inbound_inventory=OperationalValueInput(status="not_applicable"),
    )
    snapshot, values, missing, _, completeness = resolve_operational_inputs(inputs, cutoff)
    assert values["current_inventory"] == 0
    assert snapshot["inbound_inventory"]["status"] == "not_applicable"
    assert "inbound_inventory" not in missing
    assert "safety_stock" in missing
    assert completeness == "partial_data"


def test_input_available_after_cutoff_is_excluded() -> None:
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    inputs = PortfolioOperationalInputs(
        current_inventory=OperationalValueInput(
            value=100,
            status="available",
            available_at=cutoff + timedelta(seconds=1),
        )
    )
    snapshot, values, missing, warnings, _ = resolve_operational_inputs(inputs, cutoff)
    assert values["current_inventory"] is None
    assert snapshot["current_inventory"]["status"] == "missing"
    assert "current_inventory" in missing
    assert warnings == ["current_inventory:available_after_cutoff"]


def test_priority_score_renormalizes_only_valid_components() -> None:
    metrics = {
        "forecast_total": 100.0,
        "forecast_average": 10.0,
        "forecast_peak": 15.0,
        "forecast_variability": 0.2,
    }
    full = priority_score(
        metrics=metrics,
        max_forecast_total=100,
        coverage=2,
        horizon=10,
        current_inventory=20,
        safety_stock=25,
        lead_time=3,
    )
    partial = priority_score(
        metrics=metrics,
        max_forecast_total=100,
        coverage=None,
        horizon=10,
        current_inventory=None,
        safety_stock=None,
        lead_time=None,
    )
    assert full[1] == "complete"
    assert partial[1] == "partial"
    assert partial[2]["inventory_coverage"]["available"] is False
    assert 0 <= full[0] <= 100
    assert 0 <= partial[0] <= 100


def test_ranking_is_stable_and_preserves_ties() -> None:
    items = [
        {"series_key": "B", "risk_level": "high", "priority_score": 70, "forecast_total": 100},
        {"series_key": "A", "risk_level": "high", "priority_score": 70, "forecast_total": 100},
        {"series_key": "C", "risk_level": "unknown", "priority_score": 99, "forecast_total": 300},
    ]
    ranked = rank_items(items)
    assert [item["series_key"] for item in ranked] == ["A", "B", "C"]
    assert [item["rank"] for item in ranked] == [1, 1, 3]


def test_portfolio_api_preflight_persists_and_recovers_without_mutating_forecast(
    client: TestClient,
) -> None:
    forecast = _forecast(client)
    points_before = client.get(f"/api/v1/forecast-runs/{forecast['id']}/points").json()
    payload = _request(forecast)
    preflight = client.post("/api/v1/portfolio/preflight", json=payload)
    assert preflight.status_code == 200, preflight.text
    assert preflight.json()["series_compatible"] == 1
    created = client.post("/api/v1/portfolio", json=payload)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["number_of_series"] == 1
    assert body["items"][0]["forecast_run_id"] == forecast["id"]
    assert body["items"][0]["inventory_coverage"] is not None
    assert body["provenance"]["forecast_runs_modified"] is False
    assert client.get(f"/api/v1/portfolio/{body['id']}").json() == body
    assert client.get(f"/api/v1/portfolio/{body['id']}/items").status_code == 200
    assert client.get(f"/api/v1/portfolio/{body['id']}/summary").status_code == 200
    assert client.get(f"/api/v1/portfolio/{body['id']}/ranking").status_code == 200
    assert client.get("/api/v1/portfolio").json()[0]["id"] == body["id"]
    assert client.get(f"/api/v1/forecast-runs/{forecast['id']}/points").json() == points_before


def test_forecast_created_after_cutoff_is_rejected(client: TestClient) -> None:
    forecast = _forecast(client)
    payload = _request(forecast)
    payload["cutoff"] = "2020-01-01T00:00:00Z"
    response = client.post("/api/v1/portfolio/preflight", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "portfolio_forecast_unavailable"


def test_latest_compatible_forecast_is_selected_deterministically(client: TestClient) -> None:
    first = _forecast(client)
    second_response = client.post(
        "/api/v1/forecast-runs",
        json={
            "dataset_id": first["dataset_id"],
            "product": "A",
            "category": "Core",
            "location": "North",
            "frequency": "daily",
            "horizon": 7,
        },
    )
    assert second_response.status_code == 201
    second = second_response.json()
    payload = {
        "dataset_id": first["dataset_id"],
        "cutoff": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    }
    result = client.post("/api/v1/portfolio/preflight", json=payload).json()
    assert result["series_compatible"] == 1
    assert result["candidates"][0]["forecast_run_id"] == second["id"]


def test_incompatible_frequencies_are_not_aggregated(client: TestClient) -> None:
    weekly = _forecast(client, frequency="weekly")
    daily_response = client.post(
        "/api/v1/forecast-runs",
        json={
            "dataset_id": weekly["dataset_id"],
            "product": "A",
            "category": "Core",
            "location": "North",
            "frequency": "daily",
            "horizon": 7,
        },
    )
    assert daily_response.status_code == 201
    response = client.post(
        "/api/v1/portfolio/preflight",
        json={
            "forecast_run_ids": [weekly["id"], daily_response.json()["id"]],
            "cutoff": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "portfolio_incompatible_forecasts"


def test_demo_is_reproducible_decoupled_and_contains_data_states(client: TestClient) -> None:
    before = client.get("/api/v1/forecast-runs").json()
    first = client.post("/api/v1/portfolio/demo/regenerate")
    second = client.post("/api/v1/portfolio/demo/regenerate")
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    first_body = first.json()
    second_body = second.json()
    assert first_body["id"] == second_body["id"]
    assert first_body["forecast_run_ids"] == []
    assert first_body["source_mode"] == "demo"
    assert first_body["number_of_series"] == 6
    assert (
        first_body["summary"]["risk_counts"]["critical"]
        + first_body["summary"]["risk_counts"]["high"]
        == 2
    )
    assert first_body["summary"]["coverage_evaluable_series"] == 5
    assert first_body["summary"] == second_body["summary"]
    first_signature = [
        (item["series_key"], item["risk_level"], item["priority_score"], item["rank"])
        for item in first_body["items"]
    ]
    second_signature = [
        (item["series_key"], item["risk_level"], item["priority_score"], item["rank"])
        for item in second_body["items"]
    ]
    assert first_signature == second_signature
    states = {item["operational_data_completeness"] for item in first_body["items"]}
    assert states == {"sufficient_data", "partial_data", "insufficient_data"}
    tie = [item for item in first_body["items"] if item["product"] in {"NX-501", "NX-502"}]
    assert tie[0]["rank"] == tie[1]["rank"] == 3
    nx101 = next(item for item in first_body["items"] if item["product"] == "NX-101")
    assert nx101["current_inventory"] == 420
    assert nx101["forecast_average"] == pytest.approx(330.8333333333333)
    assert nx101["inventory_coverage"] == pytest.approx(420 / (1985 / 6))
    nx455 = next(item for item in first_body["items"] if item["product"] == "NX-455")
    assert nx455["current_inventory"] is None
    assert nx455["inventory_coverage"] is None
    assert nx455["coverage_status"] == "not_calculable_missing_inventory"
    assert nx455["risk_level"] == "unknown"
    assert nx455["operational_inputs"]["current_inventory"]["status"] == "missing"
    recovered = client.get(f"/api/v1/portfolio/{second_body['id']}")
    assert recovered.status_code == 200
    assert recovered.json()["summary"] == first_body["summary"]
    assert [item["series_key"] for item in recovered.json()["items"]] == [
        item["series_key"] for item in second_body["items"]
    ]
    assert client.get("/api/v1/forecast-runs").json() == before


def test_definitions_and_health_remain_available(client: TestClient) -> None:
    definitions = client.get("/api/v1/portfolio/definitions")
    assert definitions.status_code == 200
    assert definitions.json()["calculation_version"] == "portfolio_priority_v1"
    assert client.get("/health").status_code == 200
