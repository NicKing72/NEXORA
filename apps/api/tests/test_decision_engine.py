"""Decision Engine rules, temporal safety, persistence, API, and immutability."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from nexora_api.services.decisions.ranking import rank_candidates
from nexora_api.services.decisions.rules import forecast_candidates, missing_input_candidate


def _forecast(
    client: TestClient,
    *,
    growth: float = 0.5,
    frequency: str = "daily",
    horizon: int = 14,
) -> dict:
    start = date(2025, 1, 1)
    rows = ["date,product,category,location,demand,stock"]
    count = 400 if frequency == "weekly" else 90
    for index in range(count):
        demand = 20 + (index % 7) + growth * index
        rows.append(f"{start + timedelta(days=index)},A,Core,North,{demand:.3f},100")
    dataset = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("decision.csv", ("\n".join(rows) + "\n").encode(), "text/csv")},
    ).json()
    client.post(f"/api/v1/datasets/{dataset['id']}/validate")
    client.post(f"/api/v1/datasets/{dataset['id']}/ready")
    response = client.post(
        "/api/v1/forecast-runs",
        json={
            "dataset_id": dataset["id"],
            "product": "A",
            "category": "Core",
            "location": "North",
            "frequency": frequency,
            "horizon": horizon,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _scenario(
    client: TestClient,
    forecast: dict,
    *,
    kind: str = "demand_percent",
    magnitude: float = 0.10,
) -> dict:
    first = forecast["forecast_points"][0]["timestamp"]
    last = forecast["forecast_points"][-1]["timestamp"]
    absolute = kind == "demand_absolute"
    stock = kind == "stock_restriction"
    create = client.post(
        "/api/v1/scenarios",
        json={
            "forecast_run_id": forecast["id"],
            "name": f"Scenario {kind}",
            "frequency": forecast["frequency"],
            "assumptions": [
                {
                    "assumption_type": kind,
                    "label": "Supuesto de prueba",
                    "start_at": first,
                    "end_at": last,
                    "scope": {"product": "A", "location": "North"},
                    "magnitude": magnitude,
                    "unit": (
                        "capacity_ratio" if stock else "absolute" if absolute else "ratio"
                    ),
                    "application_method": (
                        "sales_capacity_cap"
                        if stock
                        else "additive"
                        if absolute
                        else "multiplicative"
                    ),
                    "source_type": "user_hypothesis",
                }
            ],
        },
    )
    assert create.status_code == 201, create.text
    execute = client.post(f"/api/v1/scenarios/{create.json()['id']}/execute")
    assert execute.status_code == 200, execute.text
    return execute.json()


def _decision(client: TestClient, forecast: dict, scenario: dict | None = None) -> dict:
    response = client.post(
        "/api/v1/decisions",
        json={
            "forecast_run_id": forecast["id"],
            "scenario_run_id": scenario["id"] if scenario else None,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _rule_evidence(trajectory: float, interval_width: float | None = 0.1) -> dict:
    return {
        "forecast_summary": {
            "trajectory_delta": trajectory,
            "mean_relative_interval_width_95": interval_width,
        },
        "champion": {"stability": {"label": "high"}, "fold_count": 5},
        "missing_operational_inputs": ["lead_time"],
    }


@pytest.mark.parametrize(
    ("trajectory", "expected_action", "expected_priority"),
    [
        (0.15, "prepare_supply", "high"),
        (0.05, "investigate_demand_increase", "medium"),
        (-0.15, "investigate_demand_drop", "high"),
        (-0.05, "investigate_demand_drop", "medium"),
        (0.01, "maintain_plan", "low"),
    ],
)
def test_forecast_trajectory_rules(
    trajectory: float, expected_action: str, expected_priority: str
) -> None:
    result = forecast_candidates(_rule_evidence(trajectory))[0]
    assert result["action_type"] == expected_action
    assert result["priority"] == expected_priority
    assert result["provenance"]["causal_claim"] is False
    assert result["provenance"]["automatic_execution"] is False


def test_wide_intervals_require_additional_review() -> None:
    candidates = forecast_candidates(_rule_evidence(0.01, 0.55))
    uncertainty = next(item for item in candidates if item["stable_key"] == "forecast:uncertainty")
    assert uncertainty["priority"] == "high"
    assert uncertainty["action_type"] == "manual_review_required"


def test_missing_inputs_never_invent_an_optimal_quantity() -> None:
    candidate = missing_input_candidate(_rule_evidence(0.1))
    assert candidate["action_type"] == "manual_review_required"
    assert "inventario óptimos" in candidate["rationale"]
    assert candidate["limitations"]


def test_ranking_ties_use_stable_catalog_and_key() -> None:
    candidates = [
        {"priority": "medium", "support_score": 0.5, "action_type": "monitor", "stable_key": "b"},
        {
            "priority": "medium",
            "support_score": 0.5,
            "action_type": "maintain_plan",
            "stable_key": "z",
        },
        {"priority": "high", "support_score": 0.2, "action_type": "monitor", "stable_key": "a"},
    ]
    ranked = rank_candidates(candidates)
    assert [item["stable_key"] for item in ranked] == ["a", "z", "b"]


def test_generation_is_deterministic_and_does_not_mutate_forecast(client: TestClient) -> None:
    forecast = _forecast(client)
    points_before = client.get(f"/api/v1/forecast-runs/{forecast['id']}/points").json()
    first = _decision(client, forecast)
    second = _decision(client, forecast)
    first_semantics = [
        (item["rank"], item["priority"], item["action_type"], item["summary"])
        for item in first["recommendations"]
    ]
    second_semantics = [
        (item["rank"], item["priority"], item["action_type"], item["summary"])
        for item in second["recommendations"]
    ]
    assert first_semantics == second_semantics
    assert first["source_snapshot"]["immutable_sources"] is True
    assert client.get(f"/api/v1/forecast-runs/{forecast['id']}/points").json() == points_before


def test_positive_and_negative_scenarios_are_explained_as_hypothetical(
    client: TestClient,
) -> None:
    forecast = _forecast(client, growth=0)
    positive = _scenario(client, forecast, magnitude=0.12)
    negative = _scenario(client, forecast, magnitude=-0.12)
    positive_run = _decision(client, forecast, positive)
    negative_run = _decision(client, forecast, negative)
    positive_item = next(
        item
        for item in positive_run["recommendations"]
        if item["action_type"] == "prepare_capacity"
    )
    negative_item = next(
        item
        for item in negative_run["recommendations"]
        if item["action_type"] == "review_inventory_policy"
    )
    assert positive_item["provenance"]["scenario_is_hypothetical"] is True
    assert negative_item["provenance"]["scenario_is_hypothetical"] is True
    assert positive_run["source_snapshot"]["scenario"]["official_forecast_modified"] is False


def test_stock_restriction_recommends_review_without_inventing_lost_demand(
    client: TestClient,
) -> None:
    forecast = _forecast(client, growth=0)
    scenario = _scenario(client, forecast, kind="stock_restriction", magnitude=0.75)
    scenario_before = client.get(f"/api/v1/scenarios/{scenario['id']}").json()
    result = _decision(client, forecast, scenario)
    item = next(
        recommendation
        for recommendation in result["recommendations"]
        if recommendation["action_type"] == "review_stockout_risk"
    )
    assert item["priority"] in {"high", "critical"}
    assert item["provenance"]["demand_censoring_possible"] is True
    assert "ventas perdidas" in item["rationale"]
    assert client.get(f"/api/v1/scenarios/{scenario['id']}").json() == scenario_before


def test_api_preflight_recovery_evidence_comparison_and_lifecycle(client: TestClient) -> None:
    forecast = _forecast(client, growth=0)
    scenario = _scenario(client, forecast, magnitude=0.08)
    preflight = client.post(
        "/api/v1/decisions/preflight",
        json={"forecast_run_id": forecast["id"], "scenario_run_id": scenario["id"]},
    )
    assert preflight.status_code == 200, preflight.text
    assert preflight.json()["missing_operational_inputs"]
    run = _decision(client, forecast, scenario)
    run_id = run["id"]
    recommendation = run["recommendations"][0]
    assert client.get("/api/v1/decisions").status_code == 200
    assert client.get(f"/api/v1/decisions/{run_id}").json() == run
    assert client.get(f"/api/v1/decisions/{run_id}/recommendations").status_code == 200
    comparison = client.get(f"/api/v1/decisions/{run_id}/compare").json()
    assert comparison["relative_delta"] == pytest.approx(0.08)
    evidence = client.get(
        f"/api/v1/decisions/recommendations/{recommendation['id']}/evidence"
    )
    assert evidence.status_code == 200
    assert evidence.json()
    changed = client.patch(
        f"/api/v1/decisions/recommendations/{recommendation['id']}/status",
        json={"status": "acknowledged", "note": "Revisado en QA"},
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "acknowledged"
    assert changed.json()["audit"][-1]["from_status"] == "open"
    assert changed.json()["audit"][-1]["to_status"] == "acknowledged"
    invalid = client.patch(
        f"/api/v1/decisions/recommendations/{recommendation['id']}/status",
        json={"status": "open"},
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "invalid_decision_status_transition"


def test_scenario_created_after_decision_cutoff_is_rejected(client: TestClient) -> None:
    forecast = _forecast(client, growth=0)
    forecast_created = datetime.fromisoformat(forecast["created_at"])
    scenario = _scenario(client, forecast, magnitude=0.05)
    cutoff = forecast_created + timedelta(microseconds=1)
    response = client.post(
        "/api/v1/decisions/preflight",
        json={
            "forecast_run_id": forecast["id"],
            "scenario_run_id": scenario["id"],
            "decision_cutoff": cutoff.isoformat(),
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "decision_scenario_after_cutoff"


def test_context_after_cutoff_is_excluded_and_valid_impact_is_traceable(
    client: TestClient,
) -> None:
    forecast = _forecast(client)
    historical = client.post(
        "/api/v1/context-signals",
        json={
            "dataset_id": forecast["dataset_id"],
            "signal_family": "commercial",
            "signal_type": "own_promotion",
            "title": "Promoción histórica",
            "description": "Evidencia descriptiva.",
            "event_start": "2025-02-10T00:00:00Z",
            "event_end": "2025-02-16T00:00:00Z",
            "observed_at": "2025-02-16T00:00:00Z",
            "available_at": "2025-02-16T00:00:00Z",
            "knowledge_type": "observed",
            "scope_type": "product",
            "product": "A",
            "category": "Core",
            "location": "North",
            "confidence": 0.9,
        },
    ).json()
    impact = client.post(
        f"/api/v1/context-impact/signals/{historical['id']}/estimate",
        json={"frequency": "daily", "data_cutoff": forecast["data_cutoff"]},
    )
    assert impact.status_code == 200
    future_available = datetime.now(UTC) + timedelta(days=3)
    late_signal = client.post(
        "/api/v1/context-signals",
        json={
            "dataset_id": forecast["dataset_id"],
            "signal_family": "commercial",
            "signal_type": "campaign",
            "title": "Campaña aún no conocida",
            "description": "Debe quedar fuera del cutoff.",
            "event_start": (future_available + timedelta(days=2)).isoformat(),
            "available_at": future_available.isoformat(),
            "knowledge_type": "known_future",
            "scope_type": "product",
            "product": "A",
            "category": "Core",
            "location": "North",
            "confidence": 0.8,
        },
    ).json()
    result = _decision(client, forecast)
    assert all(
        late_signal["id"] not in item["context_signal_ids"]
        for item in result["recommendations"]
    )
    impact_items = [
        item
        for item in result["recommendations"]
        if historical["id"] in item["context_signal_ids"]
    ]
    if impact.json()["status"] == "estimated":
        assert impact_items
        assert impact.json()["id"] in impact_items[0]["context_impact_ids"]
        assert impact_items[0]["provenance"]["causal_claim"] is False
        expected_support = 0.55 * (impact.json()["evidence_score"] / 100) + 0.45 * 0.9
        assert impact_items[0]["support_score"] == pytest.approx(expected_support, abs=1e-4)


def test_impact_estimated_after_backdated_cutoff_is_not_used(client: TestClient) -> None:
    forecast = _forecast(client)
    signal = client.post(
        "/api/v1/context-signals",
        json={
            "dataset_id": forecast["dataset_id"],
            "signal_family": "commercial",
            "signal_type": "own_promotion",
            "title": "Impacto posterior",
            "description": "Prueba de cutoff.",
            "event_start": "2025-02-10T00:00:00Z",
            "event_end": "2025-02-16T00:00:00Z",
            "observed_at": "2025-02-16T00:00:00Z",
            "available_at": "2025-02-16T00:00:00Z",
            "knowledge_type": "observed",
            "scope_type": "product",
            "product": "A",
            "category": "Core",
            "location": "North",
            "confidence": 0.9,
        },
    ).json()
    impact = client.post(
        f"/api/v1/context-impact/signals/{signal['id']}/estimate",
        json={"frequency": "daily", "data_cutoff": forecast["data_cutoff"]},
    ).json()
    forecast_created = datetime.fromisoformat(forecast["created_at"])
    impact_created = datetime.fromisoformat(impact["estimated_at"])
    cutoff = forecast_created + (impact_created - forecast_created) / 2
    preflight = client.post(
        "/api/v1/decisions/preflight",
        json={"forecast_run_id": forecast["id"], "decision_cutoff": cutoff.isoformat()},
    )
    assert preflight.status_code == 200, preflight.text
    assert all(item["id"] != impact["id"] for item in preflight.json()["usable_impacts"])


def test_health_remains_operational_with_decision_engine(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"
