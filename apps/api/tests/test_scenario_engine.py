"""Deterministic Scenario Engine behavior and REST recovery."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from nexora_api.models.scenario import ScenarioAssumption
from nexora_api.services.scenarios.combination import combine
from nexora_api.services.scenarios.transforms import apply_transform


def _forecast(client: TestClient, *, frequency: str = "daily", horizon: int = 7) -> dict:
    start = date(2024, 1, 1)
    rows = ["date,product,category,location,demand,stock"]
    count = 370 if frequency == "weekly" else 70
    for index in range(count):
        demand = 20 + index % 7
        rows.append(f"{start + timedelta(days=index)},A,Core,North,{demand},50")
    dataset = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("scenario.csv", ("\n".join(rows) + "\n").encode(), "text/csv")},
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


def _assumption(
    kind: str = "demand_percent",
    magnitude: float = 0.1,
    start: str = "2024-03-11T00:00:00Z",
    end: str | None = "2024-03-17T00:00:00Z",
) -> dict:
    absolute = kind == "demand_absolute"
    stock = kind == "stock_restriction"
    return {
        "assumption_type": kind,
        "label": "Supuesto auditable",
        "start_at": start,
        "end_at": end,
        "scope": {"product": "A", "location": "North"},
        "magnitude": magnitude,
        "unit": "capacity_ratio" if stock else "absolute" if absolute else "ratio",
        "application_method": (
            "sales_capacity_cap" if stock else "additive" if absolute else "multiplicative"
        ),
        "source_type": "user_hypothesis",
        "source_note": "Prueba determinística",
    }


@pytest.mark.parametrize(
    ("method", "magnitude", "expected"),
    [("multiplicative", 0.08, 108.0), ("additive", -12.0, 88.0)],
)
def test_percentage_and_absolute_transform(method: str, magnitude: float, expected: float) -> None:
    assert apply_transform(100, 100, method, magnitude).value == expected


def test_stock_restriction_is_a_censored_sales_cap() -> None:
    result = apply_transform(120, 100, "sales_capacity_cap", 0.6)
    assert result.value == 60
    assert result.warnings == ("sales_potentially_censored",)


def test_baseline_zero_has_no_invalid_percentage() -> None:
    assumption = ScenarioAssumption(
        id="a",
        scenario_run_id="s",
        order_index=0,
        assumption_type="demand_absolute",
        label="Absolute",
        start_at=datetime(2025, 1, 1, tzinfo=UTC),
        end_at=None,
        scope_json={},
        magnitude=5,
        unit="absolute",
        application_method="additive",
        source_type="user_hypothesis",
        provenance_json={},
        warnings=[],
    )
    points, _ = combine(
        [{"timestamp": "2025-01-01", "forecast": 0.0}],
        [assumption],
    )
    assert points[0]["scenario"] == 5
    assert points[0]["relative_delta"] is None


def test_multiple_overlapping_assumptions_are_ordered_and_warned() -> None:
    base = dict(
        scenario_run_id="s",
        start_at=datetime(2025, 1, 1, tzinfo=UTC),
        end_at=datetime(2025, 1, 2, tzinfo=UTC),
        scope_json={},
        source_type="user_hypothesis",
        provenance_json={},
        warnings=[],
    )
    assumptions = [
        ScenarioAssumption(
            id="percent", order_index=0, assumption_type="demand_percent", label="P",
            magnitude=0.1, unit="ratio", application_method="multiplicative", **base
        ),
        ScenarioAssumption(
            id="absolute", order_index=1, assumption_type="demand_absolute", label="A",
            magnitude=5, unit="absolute", application_method="additive", **base
        ),
    ]
    source = [
        {"timestamp": "2025-01-01", "forecast": 100.0},
        {"timestamp": "2025-01-03", "forecast": 100.0},
    ]
    first, warnings = combine(source, assumptions)
    second, _ = combine(source, assumptions)
    assert first == second
    assert first[0]["scenario"] == 115
    assert first[1]["scenario"] == 100
    assert warnings == ["overlapping_assumptions_applied_in_declared_order"]


def test_scenario_api_preserves_baseline_and_recovers_artifacts(client: TestClient) -> None:
    forecast = _forecast(client)
    baseline_before = client.get(f"/api/v1/forecast-runs/{forecast['id']}/points").json()
    first_date = forecast["forecast_points"][0]["timestamp"]
    last_date = forecast["forecast_points"][-1]["timestamp"]
    payload = {
        "forecast_run_id": forecast["id"],
        "name": "Promoción hipotética",
        "description": "Escenario condicionado, no forecast oficial.",
        "frequency": "daily",
        "assumptions": [_assumption("promotion", 0.08, first_date, last_date)],
    }
    preflight = client.post(
        "/api/v1/scenarios/preflight", json={"forecast_run_id": forecast["id"]}
    )
    created = client.post("/api/v1/scenarios", json=payload)
    assert preflight.status_code == 200, preflight.text
    assert created.status_code == 201, created.text
    scenario_id = created.json()["id"]
    executed = client.post(f"/api/v1/scenarios/{scenario_id}/execute")
    assert executed.status_code == 200, executed.text
    result = executed.json()
    assert result["status"] == "completed"
    assert result["summary"]["affected_periods"] == 7
    assert result["summary"]["relative_delta"] == pytest.approx(0.08)
    assert all(
        point["scenario"] == pytest.approx(point["baseline"] * 1.08)
        for point in result["points"]
    )
    assert result["provenance"]["official_forecast_modified"] is False
    assert result["baseline_snapshot"]["forecast_preprocessing"] == forecast["preprocessing"]
    assert [point["lower_95"] for point in result["points"]] == [
        point["lower_95"] for point in baseline_before
    ]
    assert client.get(f"/api/v1/scenarios/{scenario_id}").json()["points"] == result["points"]
    assert client.get(f"/api/v1/scenarios/{scenario_id}/assumptions").status_code == 200
    assert client.get(f"/api/v1/scenarios/{scenario_id}/points").status_code == 200
    assert client.get(f"/api/v1/scenarios/{scenario_id}/compare").status_code == 200
    assert client.get("/api/v1/scenarios").json()[0]["id"] == scenario_id
    assert client.get(f"/api/v1/forecast-runs/{forecast['id']}/points").json() == baseline_before


def test_frequency_cannot_change_from_daily_baseline(client: TestClient) -> None:
    forecast = _forecast(client)
    first = forecast["forecast_points"][0]["timestamp"]
    response = client.post(
        "/api/v1/scenarios",
        json={
            "forecast_run_id": forecast["id"],
            "name": "Frecuencia inválida",
            "frequency": "weekly",
            "assumptions": [_assumption(start=first, end=first)],
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "scenario_frequency_mismatch"


def test_weekly_window_affects_only_canonical_weekly_points(client: TestClient) -> None:
    forecast = _forecast(client, frequency="weekly", horizon=3)
    points = forecast["forecast_points"]
    response = client.post(
        "/api/v1/scenarios",
        json={
            "forecast_run_id": forecast["id"],
            "name": "Escenario semanal",
            "frequency": "weekly",
            "assumptions": [
                _assumption(
                    "demand_absolute", 10, points[1]["timestamp"], points[1]["timestamp"]
                )
            ],
        },
    )
    assert response.status_code == 201, response.text
    result = client.post(f"/api/v1/scenarios/{response.json()['id']}/execute").json()
    assert [point["absolute_delta"] for point in result["points"]] == [0, 10, 0]


def test_scope_mismatch_is_rejected(client: TestClient) -> None:
    forecast = _forecast(client)
    first = forecast["forecast_points"][0]["timestamp"]
    assumption = _assumption(start=first, end=first)
    assumption["scope"] = {"product": "B"}
    response = client.post(
        "/api/v1/scenarios",
        json={"forecast_run_id": forecast["id"], "name": "Scope", "assumptions": [assumption]},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "scenario_scope_mismatch"


def test_context_evidence_is_auditable_and_temporally_safe(client: TestClient) -> None:
    forecast = _forecast(client)
    signal = client.post(
        "/api/v1/context-signals",
        json={
            "dataset_id": forecast["dataset_id"],
            "signal_family": "commercial",
            "signal_type": "own_promotion",
            "title": "Promoción histórica comparable",
            "description": "Asociación descriptiva para un escenario.",
            "event_start": "2024-02-12T00:00:00Z",
            "event_end": "2024-02-18T00:00:00Z",
            "observed_at": "2024-02-18T00:00:00Z",
            "available_at": "2024-02-18T00:00:00Z",
            "knowledge_type": "observed",
            "scope_type": "product",
            "product": "A",
            "category": "Core",
            "location": "North",
            "confidence": 0.9,
        },
    )
    assert signal.status_code == 201, signal.text
    estimate = client.post(
        f"/api/v1/context-impact/signals/{signal.json()['id']}/estimate",
        json={
            "frequency": "daily",
            "data_cutoff": forecast["data_cutoff"],
            "availability_cutoff": "2024-03-10T23:59:59Z",
        },
    )
    assert estimate.status_code == 200, estimate.text
    evidence = estimate.json()
    assert evidence["status"] == "estimated"
    preflight = client.post(
        "/api/v1/scenarios/preflight", json={"forecast_run_id": forecast["id"]}
    ).json()
    option = next(
        item
        for item in preflight["eligible_context_impacts"]
        if item["signal_id"] == signal.json()["id"]
    )
    first = forecast["forecast_points"][0]["timestamp"]
    assumption = _assumption("context_impact", option["relative_delta"], first, first)
    assumption.update(
        {
            "context_signal_id": option["signal_id"],
            "context_impact_estimate_id": option["estimate_id"],
            "source_type": "historical_evidence",
        }
    )
    created = client.post(
        "/api/v1/scenarios",
        json={
            "forecast_run_id": forecast["id"],
            "name": "Con evidencia",
            "assumptions": [assumption],
        },
    )
    assert created.status_code == 201, created.text
    provenance = created.json()["assumptions"][0]["provenance"]
    assert provenance["causal_claim"] is False
    assert provenance["evidence_score"] == evidence["evidence_score"]
    assert provenance["historical_baseline"] == evidence["baseline_value"]


def test_context_signal_known_after_forecast_cutoff_is_not_offered(client: TestClient) -> None:
    forecast = _forecast(client)
    signal = client.post(
        "/api/v1/context-signals",
        json={
            "dataset_id": forecast["dataset_id"],
            "signal_family": "commercial",
            "signal_type": "own_promotion",
            "title": "Señal conocida demasiado tarde",
            "description": "No puede entrar al escenario histórico.",
            "event_start": "2024-02-12T00:00:00Z",
            "event_end": "2024-02-18T00:00:00Z",
            "observed_at": "2024-04-01T00:00:00Z",
            "available_at": "2024-04-01T00:00:00Z",
            "knowledge_type": "observed",
            "scope_type": "product",
            "product": "A",
            "category": "Core",
            "location": "North",
            "confidence": 0.9,
        },
    )
    assert signal.status_code == 201
    estimate = client.post(
        f"/api/v1/context-impact/signals/{signal.json()['id']}/estimate",
        json={"frequency": "daily", "data_cutoff": forecast["data_cutoff"]},
    )
    assert estimate.status_code == 200
    preflight = client.post(
        "/api/v1/scenarios/preflight", json={"forecast_run_id": forecast["id"]}
    ).json()
    assert all(
        item["signal_id"] != signal.json()["id"]
        for item in preflight["eligible_context_impacts"]
    )


def test_insufficient_context_evidence_cannot_be_used(client: TestClient) -> None:
    forecast = _forecast(client)
    signal = client.post(
        "/api/v1/context-signals",
        json={
            "dataset_id": forecast["dataset_id"],
            "signal_family": "commercial",
            "signal_type": "own_promotion",
            "title": "Evento sin referencias previas",
            "description": "Ocurre al inicio de la historia.",
            "event_start": "2024-01-01T00:00:00Z",
            "event_end": "2024-01-02T00:00:00Z",
            "observed_at": "2024-01-02T00:00:00Z",
            "available_at": "2024-01-02T00:00:00Z",
            "knowledge_type": "observed",
            "scope_type": "product",
            "product": "A",
            "category": "Core",
            "location": "North",
            "confidence": 0.9,
        },
    ).json()
    estimate = client.post(
        f"/api/v1/context-impact/signals/{signal['id']}/estimate",
        json={"frequency": "daily", "data_cutoff": forecast["data_cutoff"]},
    )
    assert estimate.status_code == 200
    assert estimate.json()["status"] == "insufficient_evidence"
    preflight = client.post(
        "/api/v1/scenarios/preflight", json={"forecast_run_id": forecast["id"]}
    ).json()
    assert all(
        item["estimate_id"] != estimate.json()["id"]
        for item in preflight["eligible_context_impacts"]
    )


def test_health_remains_operational_with_scenario_engine(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"
