"""Portfolio evidence integration for deterministic, non-executing decisions."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from nexora_api.services.decisions.portfolio_support import (
    PORTFOLIO_SUPPORT_RULE_VERSION,
    PORTFOLIO_THRESHOLDS,
    generate_portfolio_candidates,
    portfolio_item_support,
    reinforce_candidates,
)


def _forecast(client: TestClient, *, product: str = "A") -> dict:
    start = date(2025, 1, 1)
    rows = ["date,product,category,location,demand,stock"]
    for index in range(90):
        rows.append(
            f"{start + timedelta(days=index)},{product},Core,North,"
            f"{24 + index % 7},100"
        )
    dataset = client.post(
        "/api/v1/datasets/upload",
        files={
            "file": (
                "decision-portfolio.csv",
                ("\n".join(rows) + "\n").encode(),
                "text/csv",
            )
        },
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
            "frequency": "daily",
            "horizon": 14,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _portfolio(
    client: TestClient,
    forecast: dict,
    *,
    cutoff: datetime | None = None,
    complete: bool = True,
) -> dict:
    portfolio_cutoff = cutoff or datetime.now(UTC) + timedelta(minutes=2)
    operational_inputs: dict[str, dict] = {}
    if complete:
        operational_inputs = {
            forecast["id"]: {
                field: {
                    "value": value,
                    "status": "available",
                    "available_at": portfolio_cutoff.isoformat(),
                    "source_type": "manual",
                }
                for field, value in {
                    "current_inventory": 1,
                    "inbound_inventory": 0,
                    "safety_stock": 20,
                    "lead_time": 3,
                }.items()
            }
        }
    response = client.post(
        "/api/v1/portfolio",
        json={
            "dataset_id": forecast["dataset_id"],
            "forecast_run_ids": [forecast["id"]],
            "cutoff": portfolio_cutoff.isoformat(),
            "operational_inputs": operational_inputs,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _decision_cutoff() -> str:
    return (datetime.now(UTC) + timedelta(minutes=5)).isoformat()


def _decision(
    client: TestClient,
    forecast: dict,
    portfolio: dict | None = None,
) -> dict:
    response = client.post(
        "/api/v1/decisions",
        json={
            "forecast_run_id": forecast["id"],
            "portfolio_run_id": portfolio["id"] if portfolio else None,
            "decision_cutoff": _decision_cutoff(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _scenario(client: TestClient, forecast: dict) -> dict:
    first = forecast["forecast_points"][0]["timestamp"]
    last = forecast["forecast_points"][-1]["timestamp"]
    created = client.post(
        "/api/v1/scenarios",
        json={
            "forecast_run_id": forecast["id"],
            "name": "Escenario combinado con Portafolio",
            "frequency": forecast["frequency"],
            "assumptions": [
                {
                    "assumption_type": "demand_percent",
                    "label": "Hipótesis explícita",
                    "start_at": first,
                    "end_at": last,
                    "scope": {"product": "A", "location": "North"},
                    "magnitude": 0.05,
                    "unit": "ratio",
                    "application_method": "multiplicative",
                    "source_type": "user_hypothesis",
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    executed = client.post(f"/api/v1/scenarios/{created.json()['id']}/execute")
    assert executed.status_code == 200, executed.text
    return executed.json()


def _scor_assessment(client: TestClient, forecast: dict) -> dict:
    profile = client.post(
        "/api/v1/scor/benchmark-profiles",
        json={
            "name": "Meta combinada 7B",
            "profile_type": "company_target",
            "source": "Meta interna de prueba",
            "minimum_process_coverage": 0.5,
            "targets": [
                {
                    "metric_id": "P01",
                    "direction": "higher_is_better",
                    "target": 100,
                    "weight": 1,
                    "source": "Plan operativo",
                }
            ],
        },
    )
    assert profile.status_code == 201, profile.text
    assessment = client.post(
        "/api/v1/scor/assessments",
        json={
            "name": "Diagnóstico combinado 7B",
            "company_name": "Empresa de prueba",
            "source_dataset_id": forecast["dataset_id"],
            "benchmark_profile_id": profile.json()["id"],
            "period_start": "2026-01-01T00:00:00Z",
            "period_end": "2026-06-30T23:59:59Z",
            "cutoff": "2026-08-01T00:00:00Z",
            "source_name": "ERP de prueba",
            "source_metadata": {"scope_type": "dataset"},
            "metric_inputs": [
                {
                    "metric_id": "P01",
                    "values": {
                        "actual_units_6m": 85,
                        "forecast_units_6m": 100,
                    },
                    "available_at": "2026-08-01T00:00:00Z",
                    "source": "ERP de prueba",
                }
            ],
        },
    )
    assert assessment.status_code == 201, assessment.text
    calculated = client.post(
        f"/api/v1/scor/assessments/{assessment.json()['id']}/calculate"
    )
    assert calculated.status_code == 200, calculated.text
    return calculated.json()


def _item(*, complete: bool = True) -> dict[str, object]:
    available = {
        key: {"status": "available", "value": value}
        for key, value in {
            "current_inventory": 1,
            "inbound_inventory": 0,
            "safety_stock": 20,
            "lead_time": 3,
        }.items()
    }
    if not complete:
        available["current_inventory"] = {"status": "missing", "value": None}
    return {
        "id": "item-1",
        "rank": 1,
        "product": "A",
        "location": "North",
        "priority_score": 80.0,
        "risk_level": "critical" if complete else "unknown",
        "score_status": "complete" if complete else "partial",
        "operational_inputs": available,
        "inventory_coverage": 0.04 if complete else None,
        "missing_inputs": [] if complete else ["current_inventory"],
        "forecast_variability": 0.3,
    }


def _snapshot(item: dict[str, object]) -> dict[str, object]:
    return {
        "portfolio_run_id": "portfolio-1",
        "cutoff": "2026-01-01T00:00:00+00:00",
        "created_at": "2026-01-01T00:00:00+00:00",
        "available_at": "2026-01-01T00:00:00+00:00",
        "calculation_version": "portfolio_v1",
        "number_of_series": 1,
        "summary": {},
        "forecast_run_ids": ["forecast-1"],
        "provenance": {},
        "decision_cutoff": "2026-01-02T00:00:00+00:00",
        "related_items": [item],
    }


def test_portfolio_support_formula_is_exact_versioned_and_deterministic() -> None:
    item = _item()
    first = portfolio_item_support(item)
    second = portfolio_item_support(deepcopy(item))
    assert first == second
    score, factors = first
    expected = (
        0.40 * 0.8
        + 0.25 * 1.0
        + 0.15 * 1.0
        + 0.10 * 1.0
        + 0.10 * 1.0
    )
    assert score == pytest.approx(expected)
    assert factors["operational_availability"] == 1
    assert PORTFOLIO_SUPPORT_RULE_VERSION == "decision_portfolio_support_v1"
    assert PORTFOLIO_THRESHOLDS["maximum_reinforcement"] == 0.20


def test_missing_operational_data_is_not_invented_or_given_high_support() -> None:
    portfolio = _snapshot(_item(complete=False))
    candidates = generate_portfolio_candidates(portfolio)
    request = next(item for item in candidates if item["action_type"] == "complete_portfolio_data")
    assert request["priority"] == "medium"
    assert request["support_score"] <= 0.45
    assert request["provenance"]["portfolio_origin"] == "evidence_request"
    assert "current_inventory" in request["summary"]
    assert all(item["action_type"] != "review_portfolio_coverage" for item in candidates)


def test_reinforcement_is_capped_auditable_and_does_not_mutate_input() -> None:
    candidate = {
        "stable_key": "forecast:growth",
        "priority": "medium",
        "action_type": "prepare_supply",
        "support_score": 0.7,
        "evidence_level": "moderate",
        "evidence": [],
        "limitations": [],
        "provenance": {},
    }
    original = deepcopy(candidate)
    reinforced = reinforce_candidates([candidate], _snapshot(_item()))[0]
    assert candidate == original
    assert 0 < reinforced["provenance"]["portfolio_support_contribution"] <= 0.20
    assert reinforced["support_score"] == pytest.approx(
        original["support_score"]
        + reinforced["provenance"]["portfolio_support_contribution"]
    )
    assert reinforced["priority"] == "high"
    assert reinforced["provenance"]["portfolio_origin"] == "reinforced"


def test_without_portfolio_preserves_legacy_decision_semantics(client: TestClient) -> None:
    forecast = _forecast(client)
    first = _decision(client, forecast)
    second = _decision(client, forecast)
    def semantics(run: dict) -> list[tuple]:
        return [
            (
                item["rank"],
                item["priority"],
                item["action_type"],
                item["support_score"],
            )
            for item in run["recommendations"]
        ]
    assert semantics(first) == semantics(second)
    assert first["portfolio_run_id"] is None
    assert first["source_snapshot"]["portfolio"] is None
    assert first["summary"]["portfolios_considered"] == 0


def test_portfolio_is_listed_selected_persisted_and_recovered(client: TestClient) -> None:
    forecast = _forecast(client)
    portfolio = _portfolio(client, forecast)
    forecast_points = client.get(f"/api/v1/forecast-runs/{forecast['id']}/points").json()
    portfolio_before = client.get(f"/api/v1/portfolio/{portfolio['id']}").json()
    payload = {
        "forecast_run_id": forecast["id"],
        "portfolio_run_id": portfolio["id"],
        "decision_cutoff": _decision_cutoff(),
    }
    preflight = client.post("/api/v1/decisions/preflight", json=payload)
    assert preflight.status_code == 200, preflight.text
    assert [item["id"] for item in preflight.json()["portfolios"]] == [portfolio["id"]]
    assert preflight.json()["selected_portfolio"]["portfolio_run_id"] == portfolio["id"]
    created = client.post("/api/v1/decisions", json=payload)
    assert created.status_code == 201, created.text
    run = created.json()
    assert run["portfolio_run_id"] == portfolio["id"]
    assert run["summary"]["portfolios_considered"] == 1
    assert run["summary"]["portfolio_recommendation_count"] >= 1
    assert run["source_snapshot"]["portfolio"]["snapshot_immutable"] is True
    assert client.get(f"/api/v1/decisions/{run['id']}").json() == run
    assert client.get(f"/api/v1/forecast-runs/{forecast['id']}/points").json() == forecast_points
    assert client.get(f"/api/v1/portfolio/{portfolio['id']}").json() == portfolio_before


def test_exact_requested_portfolio_is_selected_among_multiple_compatible_runs(
    client: TestClient,
) -> None:
    forecast = _forecast(client)
    first = _portfolio(
        client,
        forecast,
        cutoff=datetime.now(UTC) + timedelta(minutes=1),
        complete=False,
    )
    second = _portfolio(
        client,
        forecast,
        cutoff=datetime.now(UTC) + timedelta(minutes=2),
        complete=True,
    )
    base_payload = {
        "forecast_run_id": forecast["id"],
        "decision_cutoff": _decision_cutoff(),
    }
    legacy = client.post("/api/v1/decisions/preflight", json=base_payload)
    assert legacy.status_code == 200
    assert {item["id"] for item in legacy.json()["portfolios"]} == {
        first["id"],
        second["id"],
    }
    assert legacy.json()["selected_portfolio"] is None

    selected = client.post(
        "/api/v1/decisions/preflight",
        json={**base_payload, "portfolio_run_id": first["id"]},
    )
    assert selected.status_code == 200, selected.text
    assert selected.json()["selected_portfolio"]["portfolio_run_id"] == first["id"]
    assert selected.json()["selected_portfolio"]["portfolio_run_id"] != second["id"]


def test_nonexistent_portfolio_is_not_replaced_by_a_compatible_run(
    client: TestClient,
) -> None:
    forecast = _forecast(client)
    compatible = _portfolio(client, forecast)
    response = client.post(
        "/api/v1/decisions/preflight",
        json={
            "forecast_run_id": forecast["id"],
            "portfolio_run_id": "00000000-0000-4000-8000-000000000001",
            "decision_cutoff": _decision_cutoff(),
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "decision_portfolio_not_found"
    listed = client.post(
        "/api/v1/decisions/preflight",
        json={
            "forecast_run_id": forecast["id"],
            "decision_cutoff": _decision_cutoff(),
        },
    ).json()
    assert [item["id"] for item in listed["portfolios"]] == [compatible["id"]]
    assert listed["selected_portfolio"] is None


def test_portfolio_evidence_endpoint_and_lifecycle_survive_recovery(client: TestClient) -> None:
    forecast = _forecast(client)
    run = _decision(client, forecast, _portfolio(client, forecast))
    recommendation = next(
        item for item in run["recommendations"] if item["portfolio_origin"] is not None
    )
    evidence = client.get(
        f"/api/v1/decisions/recommendations/{recommendation['id']}/portfolio-evidence"
    )
    assert evidence.status_code == 200
    assert evidence.json()
    assert all(item["evidence_type"].startswith("portfolio_") for item in evidence.json())
    changed = client.patch(
        f"/api/v1/decisions/recommendations/{recommendation['id']}/status",
        json={"status": "acknowledged", "note": "QA Portafolio"},
    )
    assert changed.status_code == 200
    recovered = client.get(f"/api/v1/decisions/{run['id']}").json()
    recovered_item = next(
        item for item in recovered["recommendations"] if item["id"] == recommendation["id"]
    )
    assert recovered_item["status"] == "acknowledged"
    assert recovered_item["portfolio_run_id"] == run["portfolio_run_id"]
    assert any(
        item["evidence_type"].startswith("portfolio_")
        for item in recovered_item["evidence"]
    )


def test_portfolio_available_after_decision_cutoff_is_rejected(client: TestClient) -> None:
    forecast = _forecast(client)
    future_cutoff = datetime.now(UTC) + timedelta(minutes=10)
    portfolio = _portfolio(client, forecast, cutoff=future_cutoff)
    response = client.post(
        "/api/v1/decisions/preflight",
        json={
            "forecast_run_id": forecast["id"],
            "portfolio_run_id": portfolio["id"],
            "decision_cutoff": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] in {
        "decision_portfolio_after_cutoff",
        "decision_portfolio_future_state",
    }


def test_demo_and_incompatible_portfolios_are_rejected(client: TestClient) -> None:
    forecast = _forecast(client)
    demo = client.post("/api/v1/portfolio/demo/regenerate").json()
    demo_response = client.post(
        "/api/v1/decisions/preflight",
        json={
            "forecast_run_id": forecast["id"],
            "portfolio_run_id": demo["id"],
            "decision_cutoff": _decision_cutoff(),
        },
    )
    assert demo_response.status_code == 409
    assert demo_response.json()["error"]["code"] == "decision_portfolio_demo_not_allowed"

    other_forecast = _forecast(client, product="B")
    other_portfolio = _portfolio(client, other_forecast)
    mismatch = client.post(
        "/api/v1/decisions/preflight",
        json={
            "forecast_run_id": forecast["id"],
            "portfolio_run_id": other_portfolio["id"],
            "decision_cutoff": _decision_cutoff(),
        },
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "decision_portfolio_incompatible"


def test_frozen_portfolio_snapshot_is_not_changed_by_new_portfolio_run(
    client: TestClient,
) -> None:
    forecast = _forecast(client)
    first_portfolio = _portfolio(client, forecast)
    decision = _decision(client, forecast, first_portfolio)
    frozen = deepcopy(decision["source_snapshot"]["portfolio"])
    _portfolio(
        client,
        forecast,
        cutoff=datetime.now(UTC) + timedelta(minutes=3),
        complete=False,
    )
    recovered = client.get(f"/api/v1/decisions/{decision['id']}").json()
    assert recovered["source_snapshot"]["portfolio"] == frozen
    assert recovered["portfolio_run_id"] == first_portfolio["id"]


def test_portfolio_coexists_with_scenario_and_scor_without_mutating_sources(
    client: TestClient,
) -> None:
    forecast = _forecast(client)
    portfolio = _portfolio(client, forecast)
    scenario = _scenario(client, forecast)
    assessment = _scor_assessment(client, forecast)
    forecast_before = client.get(f"/api/v1/forecast-runs/{forecast['id']}").json()
    scenario_before = client.get(f"/api/v1/scenarios/{scenario['id']}").json()
    portfolio_before = client.get(f"/api/v1/portfolio/{portfolio['id']}").json()
    response = client.post(
        "/api/v1/decisions",
        json={
            "forecast_run_id": forecast["id"],
            "scenario_run_id": scenario["id"],
            "scor_assessment_id": assessment["id"],
            "portfolio_run_id": portfolio["id"],
            "decision_cutoff": _decision_cutoff(),
        },
    )
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["scenario_run_id"] == scenario["id"]
    assert run["scor_assessment_id"] == assessment["id"]
    assert run["portfolio_run_id"] == portfolio["id"]
    assert run["source_snapshot"]["scenario"]["hypothetical"] is True
    assert run["source_snapshot"]["scor"]["scor_assessment_id"] == assessment["id"]
    assert run["source_snapshot"]["portfolio"]["snapshot_immutable"] is True
    assert client.get(f"/api/v1/forecast-runs/{forecast['id']}").json() == forecast_before
    assert client.get(f"/api/v1/scenarios/{scenario['id']}").json() == scenario_before
    assert client.get(f"/api/v1/portfolio/{portfolio['id']}").json() == portfolio_before


def test_health_remains_operational(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
