"""SCOR evidence integration for deterministic, non-causal decision support."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from nexora_api.services.decisions.scor_support import (
    SCOR_SUPPORT_RULE_VERSION,
    SCOR_THRESHOLDS,
    scor_metric_support,
)


def _forecast(client: TestClient) -> dict:
    start = date(2025, 1, 1)
    rows = ["date,product,category,location,demand,stock"]
    for index in range(90):
        rows.append(f"{start + timedelta(days=index)},A,Core,North,{24 + index % 7},100")
    dataset = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("decision-scor.csv", ("\n".join(rows) + "\n").encode(), "text/csv")},
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
            "frequency": "daily",
            "horizon": 14,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _profile(client: TestClient, *, name: str = "Metas SCOR integración") -> dict:
    targets = [
        ("P01", "higher_is_better", 100),
        ("D01", "higher_is_better", 96),
        ("D02", "higher_is_better", 100),
        ("D03", "higher_is_better", 100),
        ("D04", "higher_is_better", 100),
        ("D05", "higher_is_better", 90),
    ]
    response = client.post(
        "/api/v1/scor/benchmark-profiles",
        json={
            "name": name,
            "profile_type": "company_target",
            "source": "Metas internas de prueba",
            "minimum_process_coverage": 0.5,
            "targets": [
                {
                    "metric_id": metric_id,
                    "direction": direction,
                    "target": target,
                    "weight": 1,
                    "source": "Plan operativo",
                }
                for metric_id, direction, target in targets
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _assessment(client: TestClient, forecast: dict) -> dict:
    available = "2026-08-01T00:00:00Z"
    inputs = [
        ("P01", {"actual_units_6m": 100, "forecast_units_6m": 100}, False),
        ("D01", {"deliveries_on_time_6m": 40, "dispatched_orders_6m": 100}, False),
        ("D02", {"complete_deliveries_6m": 100, "dispatched_orders_6m": 100}, False),
        ("D03", {"damage_free_deliveries_6m": 100, "dispatched_orders_6m": 100}, False),
        ("D04", {"correctly_invoiced_orders_6m": 100, "dispatched_orders_6m": 100}, False),
        ("S02", {"received_units_6m": 100}, False),
        ("S04", {}, True),
        ("R03", {"salvaged_or_reconditioned_units_6m": 0, "returned_units_6m": 0}, False),
    ]
    response = client.post(
        "/api/v1/scor/assessments",
        json={
            "name": "Diagnóstico asociado a decisiones",
            "company_name": "Empresa de prueba",
            "source_dataset_id": forecast["dataset_id"],
            "benchmark_profile_id": _profile(client)["id"],
            "period_start": "2026-01-01T00:00:00Z",
            "period_end": "2026-06-30T23:59:59Z",
            "cutoff": available,
            "source_name": "ERP acumulado",
            "source_metadata": {"scope_type": "dataset"},
            "metric_inputs": [
                {
                    "metric_id": metric_id,
                    "values": values,
                    "not_applicable": not_applicable,
                    "available_at": available,
                    "source": "ERP acumulado",
                    "provenance": {"report": "SCOR-2026-S1"},
                }
                for metric_id, values, not_applicable in inputs
            ],
        },
    )
    assert response.status_code == 201, response.text
    calculated = client.post(f"/api/v1/scor/assessments/{response.json()['id']}/calculate")
    assert calculated.status_code == 200, calculated.text
    return calculated.json()


def _cutoff() -> str:
    return (datetime.now(UTC) + timedelta(minutes=1)).isoformat()


def _decision(client: TestClient, forecast: dict, assessment_id: str | None) -> dict:
    response = client.post(
        "/api/v1/decisions",
        json={
            "forecast_run_id": forecast["id"],
            "scor_assessment_id": assessment_id,
            "decision_cutoff": _cutoff(),
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
            "name": "Escenario inmutable con SCOR",
            "frequency": forecast["frequency"],
            "assumptions": [
                {
                    "assumption_type": "demand_percent",
                    "label": "Hipótesis explícita",
                    "start_at": first,
                    "end_at": last,
                    "scope": {"product": "A", "location": "North"},
                    "magnitude": 0.08,
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


def _semantics(run: dict) -> list[tuple]:
    return [
        (
            item["rank"],
            item["priority"],
            item["action_type"],
            item["summary"],
            item["support_score"],
        )
        for item in run["recommendations"]
    ]


def test_decision_without_scor_preserves_legacy_behavior(client: TestClient) -> None:
    forecast = _forecast(client)
    first = _decision(client, forecast, None)
    second = _decision(client, forecast, None)
    assert _semantics(first) == _semantics(second)
    assert first["scor_assessment_id"] is None
    assert first["summary"]["scor_assessments_considered"] == 0


def test_valid_scor_assessment_is_listed_selected_and_persisted(client: TestClient) -> None:
    forecast = _forecast(client)
    assessment = _assessment(client, forecast)
    preflight = client.post(
        "/api/v1/decisions/preflight",
        json={
            "forecast_run_id": forecast["id"],
            "scor_assessment_id": assessment["id"],
            "decision_cutoff": _cutoff(),
        },
    )
    assert preflight.status_code == 200, preflight.text
    assert [item["id"] for item in preflight.json()["scor_assessments"]] == [assessment["id"]]
    assert preflight.json()["selected_scor"]["scor_assessment_id"] == assessment["id"]
    run = _decision(client, forecast, assessment["id"])
    recovered = client.get(f"/api/v1/decisions/{run['id']}").json()
    assert recovered == run
    assert run["scor_assessment_id"] == assessment["id"]
    assert run["summary"]["scor_assessments_considered"] == 1


def test_assessment_calculated_after_decision_cutoff_is_rejected(client: TestClient) -> None:
    forecast = _forecast(client)
    assessment = _assessment(client, forecast)
    forecast_created = datetime.fromisoformat(forecast["created_at"])
    assessment_calculated = datetime.fromisoformat(assessment["calculated_at"])
    historical_cutoff = forecast_created + (assessment_calculated - forecast_created) / 2
    response = client.post(
        "/api/v1/decisions/preflight",
        json={
            "forecast_run_id": forecast["id"],
            "scor_assessment_id": assessment["id"],
            "decision_cutoff": historical_cutoff.isoformat(),
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "decision_scor_after_cutoff"


def test_metric_available_after_assessment_cutoff_is_blocked_at_source(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/scor/assessments",
        json={
            "name": "Input futuro",
            "period_start": "2026-01-01T00:00:00Z",
            "period_end": "2026-06-30T00:00:00Z",
            "cutoff": "2026-07-01T00:00:00Z",
            "source_name": "Manual",
            "metric_inputs": [
                {
                    "metric_id": "P01",
                    "values": {"actual_units_6m": 100, "forecast_units_6m": 100},
                    "available_at": "2026-07-02T00:00:00Z",
                }
            ],
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "scor_temporal_leakage_blocked"


def test_incomplete_insufficient_and_not_applicable_metrics_are_not_gap_alerts(
    client: TestClient,
) -> None:
    forecast = _forecast(client)
    assessment = _assessment(client, forecast)
    run = _decision(client, forecast, assessment["id"])
    scor_metric_ids = {
        item["evidence"][0]["snapshot"].get("metric", {}).get("metric_id")
        for item in run["recommendations"]
        if item["scor_origin"] == "originated" and item["evidence"]
    }
    assert "S02" not in scor_metric_ids
    assert "R03" not in scor_metric_ids
    assert "S04" not in scor_metric_ids
    completion = next(
        item for item in run["recommendations"] if item["action_type"] == "complete_scor_evidence"
    )
    assert completion["support_score"] < 0.35
    assert completion["evidence_level"] == "insufficient"


def test_high_gap_with_complete_evidence_can_raise_priority(client: TestClient) -> None:
    forecast = _forecast(client)
    assessment = _assessment(client, forecast)
    run = _decision(client, forecast, assessment["id"])
    deliver = next(
        item
        for item in run["recommendations"]
        if item["action_type"] == "review_scor_deliver"
    )
    assert deliver["priority"] == "high"
    assert deliver["support_score"] >= 0.65
    assert deliver["provenance"]["causal_claim"] is False
    assert deliver["provenance"]["automatic_execution"] is False


def test_zero_gap_does_not_create_artificial_metric_alert(client: TestClient) -> None:
    forecast = _forecast(client)
    assessment = _assessment(client, forecast)
    run = _decision(client, forecast, assessment["id"])
    assert all(
        "scor:metric:P01" != item["provenance"]["stable_key"]
        for item in run["recommendations"]
    )


def test_scor_support_formula_is_versioned_bounded_and_requires_evidence() -> None:
    metric = {
        "metric_id": "D01",
        "process": "DELIVER",
        "evidence_status": "complete",
        "gap_score": 50,
        "process_coverage": 0.8,
    }
    criticality = {"selected_process": "DELIVER", "tied_processes": []}
    assert SCOR_SUPPORT_RULE_VERSION == "decision_scor_support_v1"
    assert SCOR_THRESHOLDS["high_gap"] == 35
    assert scor_metric_support(metric, criticality) == pytest.approx(0.7)
    assert scor_metric_support({**metric, "evidence_status": "incomplete"}, criticality) == 0


def test_scor_snapshot_and_benchmark_target_remain_immutable(client: TestClient) -> None:
    forecast = _forecast(client)
    assessment = _assessment(client, forecast)
    run = _decision(client, forecast, assessment["id"])
    snapshot_before = run["source_snapshot"]["scor"]
    zero_profile = _profile(client, name="Metas posteriores")
    changed = client.post(
        f"/api/v1/scor/assessments/{assessment['id']}/benchmark",
        json={"benchmark_profile_id": zero_profile["id"]},
    )
    assert changed.status_code == 200
    recovered = client.get(f"/api/v1/decisions/{run['id']}").json()
    assert recovered["source_snapshot"]["scor"] == snapshot_before


def test_scor_recommendation_evidence_endpoint_and_lifecycle_survive_reload(
    client: TestClient,
) -> None:
    forecast = _forecast(client)
    assessment = _assessment(client, forecast)
    run = _decision(client, forecast, assessment["id"])
    recommendation = next(item for item in run["recommendations"] if item["scor_origin"])
    evidence = client.get(
        f"/api/v1/decisions/recommendations/{recommendation['id']}/scor-evidence"
    )
    assert evidence.status_code == 200
    assert evidence.json()
    assert all(item["evidence_type"].startswith("scor_") for item in evidence.json())
    changed = client.patch(
        f"/api/v1/decisions/recommendations/{recommendation['id']}/status",
        json={"status": "acknowledged", "note": "QA SCOR"},
    )
    assert changed.status_code == 200
    recovered = client.get(
        f"/api/v1/decisions/recommendations/{recommendation['id']}"
    ).json()
    assert recovered["status"] == "acknowledged"
    assert recovered["scor_assessment_id"] == assessment["id"]
    assert recovered["evidence"] == changed.json()["evidence"]


def test_scor_run_is_deterministic_and_does_not_mutate_sources(client: TestClient) -> None:
    forecast = _forecast(client)
    assessment = _assessment(client, forecast)
    forecast_before = client.get(f"/api/v1/forecast-runs/{forecast['id']}").json()
    assessment_before = client.get(f"/api/v1/scor/assessments/{assessment['id']}").json()
    first = _decision(client, forecast, assessment["id"])
    second = _decision(client, forecast, assessment["id"])
    assert _semantics(first) == _semantics(second)
    assert client.get(f"/api/v1/forecast-runs/{forecast['id']}").json() == forecast_before
    assert client.get(f"/api/v1/scor/assessments/{assessment['id']}").json() == assessment_before


def test_scor_reinforcement_is_bounded_and_explicit(client: TestClient) -> None:
    forecast = _forecast(client)
    assessment = _assessment(client, forecast)
    run = _decision(client, forecast, assessment["id"])
    reinforced = [item for item in run["recommendations"] if item["scor_origin"] == "reinforced"]
    assert reinforced
    assert all(0 < item["scor_support_contribution"] <= 0.2 for item in reinforced)
    assert all("base_support_score" in item["provenance"] for item in reinforced)


def test_scor_decision_does_not_mutate_scenario(client: TestClient) -> None:
    forecast = _forecast(client)
    assessment = _assessment(client, forecast)
    scenario = _scenario(client, forecast)
    before = client.get(f"/api/v1/scenarios/{scenario['id']}").json()
    response = client.post(
        "/api/v1/decisions",
        json={
            "forecast_run_id": forecast["id"],
            "scenario_run_id": scenario["id"],
            "scor_assessment_id": assessment["id"],
            "decision_cutoff": _cutoff(),
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["source_snapshot"]["scenario"]["hypothetical"] is True
    assert client.get(f"/api/v1/scenarios/{scenario['id']}").json() == before


def test_tied_scor_processes_never_force_a_winner(client: TestClient) -> None:
    forecast = _forecast(client)
    demo = client.post("/api/v1/scor/demo/regenerate").json()["assessment"]
    profiles = client.get("/api/v1/scor/benchmark-profiles").json()
    tie_profile = next(item for item in profiles if "empate controlado" in item["name"])
    tied = client.post(
        f"/api/v1/scor/assessments/{demo['id']}/benchmark",
        json={"benchmark_profile_id": tie_profile["id"]},
    ).json()
    assert tied["criticality"]["status"] == "tie"
    assert tied["criticality"]["selected_process"] is None
    run = _decision(client, forecast, tied["id"])
    frozen = run["source_snapshot"]["scor"]["criticality"]
    assert frozen["status"] == "tie"
    assert len(frozen["tied_processes"]) == 5
    assert all(item["action_type"] != "review_scor_critical" for item in run["recommendations"])


def test_uncalculated_scor_assessment_is_rejected(client: TestClient) -> None:
    forecast = _forecast(client)
    created = client.post(
        "/api/v1/scor/assessments",
        json={
            "name": "Borrador no utilizable",
            "source_dataset_id": forecast["dataset_id"],
            "period_start": "2026-01-01T00:00:00Z",
            "period_end": "2026-06-30T00:00:00Z",
            "cutoff": "2026-08-01T00:00:00Z",
            "source_name": "Manual",
            "metric_inputs": [],
        },
    )
    assert created.status_code == 201
    response = client.post(
        "/api/v1/decisions/preflight",
        json={
            "forecast_run_id": forecast["id"],
            "scor_assessment_id": created.json()["id"],
            "decision_cutoff": _cutoff(),
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "decision_scor_after_cutoff"


def test_incompatible_assessment_is_rejected(client: TestClient) -> None:
    forecast = _forecast(client)
    other = _forecast(client)
    assessment = _assessment(client, other)
    response = client.post(
        "/api/v1/decisions/preflight",
        json={
            "forecast_run_id": forecast["id"],
            "scor_assessment_id": assessment["id"],
            "decision_cutoff": _cutoff(),
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "decision_scor_incompatible"


def test_invalid_scor_uuid_is_rejected_by_typed_api(client: TestClient) -> None:
    forecast = _forecast(client)
    response = client.post(
        "/api/v1/decisions/preflight",
        json={"forecast_run_id": forecast["id"], "scor_assessment_id": "not-a-uuid"},
    )
    assert response.status_code == 422


def test_health_remains_operational_with_scor_decisions(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"
