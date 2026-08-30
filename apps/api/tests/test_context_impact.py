"""Deterministic coverage for Context Impact & Evidence Engine."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient


def prepare_ready_csv(client: TestClient, rows: list[str]) -> dict[str, object]:
    content = "date,product,category,location,demand,stock\n" + "\n".join(rows) + "\n"
    uploaded = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("impact.csv", content.encode(), "text/csv")},
    )
    assert uploaded.status_code == 201, uploaded.text
    dataset = uploaded.json()
    mappings = [
        {"column_name": item["column_name"], "role": item["role"]}
        for item in dataset["mappings"]
    ]
    assert client.put(
        f"/api/v1/datasets/{dataset['id']}/mappings", json={"mappings": mappings}
    ).status_code == 200
    validation = client.post(f"/api/v1/datasets/{dataset['id']}/validate")
    assert validation.status_code == 200, validation.text
    ready = client.post(f"/api/v1/datasets/{dataset['id']}/ready")
    assert ready.status_code == 200, ready.text
    return ready.json()["dataset"]


def daily_dataset(
    client: TestClient,
    *,
    event_value: str = "120",
    baseline_value: int = 100,
    days: int = 100,
    event_start_index: int = 63,
    event_days: int = 7,
) -> dict[str, object]:
    start = date(2025, 1, 1)
    rows: list[str] = []
    for index in range(days):
        demand = (
            event_value
            if event_start_index <= index < event_start_index + event_days
            else str(baseline_value)
        )
        stock = "0" if demand == "0" else "50"
        rows.append(f"{start + timedelta(days=index)},A,Core,North,{demand},{stock}")
    return prepare_ready_csv(client, rows)


def create_signal(
    client: TestClient,
    dataset_id: str,
    *,
    title: str = "Promoción histórica",
    signal_type: str = "own_promotion",
    event_start: str = "2025-03-05T00:00:00Z",
    event_end: str | None = "2025-03-11T23:59:59Z",
    available_at: str = "2025-03-01T00:00:00Z",
    knowledge_type: str = "observed",
    scope_type: str = "product",
    product: str | None = "A",
    category: str | None = None,
    location: str | None = "North",
    confidence: float = 1.0,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/context-signals",
        json={
            "dataset_id": dataset_id,
            "signal_family": "operations" if signal_type == "stockout" else "commercial",
            "signal_type": signal_type,
            "title": title,
            "description": "Evidencia determinística para pruebas.",
            "event_start": event_start,
            "event_end": event_end,
            "observed_at": event_start if knowledge_type == "observed" else None,
            "available_at": available_at,
            "knowledge_type": knowledge_type,
            "scope_type": scope_type,
            "product": product,
            "category": category,
            "location": location,
            "confidence": confidence,
            "metadata": {},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def estimate(
    client: TestClient, signal_id: str, **payload: object
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/context-impact/signals/{signal_id}/estimate",
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_positive_negative_and_neutral_observed_associations(client: TestClient) -> None:
    expectations = [("120", "increase", 0.2), ("80", "decrease", -0.2), ("102", "neutral", 0.02)]
    for value, direction, delta in expectations:
        dataset = daily_dataset(client, event_value=value)
        signal = create_signal(client, str(dataset["id"]), title=f"Evento {value}")
        result = estimate(client, str(signal["id"]))
        assert result["status"] == "estimated"
        assert result["direction"] == direction
        assert result["baseline_value"] == 100.0
        assert result["observed_value"] == float(value)
        assert abs(result["relative_delta"] - delta) < 1e-9
        assert result["method"] == "weekday_matched_trailing_8_weeks"


def test_zero_baseline_and_short_history_are_explicit(client: TestClient) -> None:
    zero_dataset = daily_dataset(client, baseline_value=0, event_value="10")
    zero_signal = create_signal(client, str(zero_dataset["id"]))
    zero = estimate(client, str(zero_signal["id"]))
    assert zero["status"] == "insufficient_evidence"
    assert zero["reason_code"] == "zero_baseline"
    assert zero["absolute_delta"] == 10.0
    assert zero["relative_delta"] is None

    short_dataset = daily_dataset(
        client, days=6, event_start_index=2, event_days=2, event_value="120"
    )
    short_signal = create_signal(
        client,
        str(short_dataset["id"]),
        event_start="2025-01-03T00:00:00Z",
        event_end="2025-01-04T23:59:59Z",
        available_at="2025-01-02T00:00:00Z",
    )
    short = estimate(client, str(short_signal["id"]))
    assert short["status"] == "insufficient_evidence"
    assert short["reason_code"] == "insufficient_reference_periods"


def test_future_incomplete_and_scenario_outcomes_are_not_invented(client: TestClient) -> None:
    dataset = daily_dataset(client)
    future = create_signal(
        client,
        str(dataset["id"]),
        event_start="2026-01-10T00:00:00Z",
        event_end="2026-01-15T00:00:00Z",
        available_at="2025-03-01T00:00:00Z",
        knowledge_type="known_future",
    )
    future_result = estimate(client, str(future["id"]))
    assert future_result["status"] == "not_observable"
    assert future_result["reason_code"] == "event_after_data_cutoff"
    assert future_result["observed_value"] is None

    scenario = create_signal(client, str(dataset["id"]), knowledge_type="scenario")
    scenario_result = estimate(client, str(scenario["id"]))
    assert scenario_result["status"] == "not_applicable"
    assert scenario_result["reason_code"] == "scenario_has_no_observed_outcome"


def test_stockout_is_censored_and_never_transferable(client: TestClient) -> None:
    dataset = daily_dataset(client, event_value="0")
    signal = create_signal(client, str(dataset["id"]), signal_type="stockout")
    result = estimate(client, str(signal["id"]))
    assert result["status"] == "not_observable"
    assert result["reason_code"] == "demand_censored_by_stockout"
    assert result["direction"] == "unknown"
    assert result["observed_value"] == 0.0
    assert result["quality_summary"]["possible_stockout_observations"] == 7


def test_missing_outliers_and_overlaps_remain_auditable(client: TestClient) -> None:
    dataset = daily_dataset(client, event_value="1000")
    primary = create_signal(client, str(dataset["id"]), title="Evento principal")
    create_signal(
        client,
        str(dataset["id"]),
        title="Evento superpuesto",
        signal_type="campaign",
    )
    result = estimate(client, str(primary["id"]))
    assert result["quality_summary"]["outliers_preserved"] is True
    assert result["quality_summary"]["outlier_observations"] > 0
    assert result["quality_summary"]["overlapping_signals"] == 1
    assert result["quality_summary"]["missing_values_imputed"] is False

    missing_dataset = daily_dataset(client, event_value="")
    missing_signal = create_signal(client, str(missing_dataset["id"]))
    missing = estimate(client, str(missing_signal["id"]))
    assert missing["status"] == "not_observable"
    assert missing["quality_summary"]["missing_periods"] == 7


def test_available_at_and_data_cutoff_are_independent_anti_leakage_guards(
    client: TestClient,
) -> None:
    dataset = daily_dataset(client)
    signal = create_signal(
        client, str(dataset["id"]), available_at="2025-03-08T00:00:00Z"
    )
    unavailable = estimate(
        client,
        str(signal["id"]),
        availability_cutoff="2025-03-07T23:59:59Z",
    )
    assert unavailable["status"] == "not_observable"
    assert unavailable["reason_code"] == "signal_unavailable_at_cutoff"
    assert unavailable["input_snapshot"]["signal"]["available_at"].startswith(
        "2025-03-08"
    )

    no_outcome = estimate(client, str(signal["id"]), data_cutoff="2025-03-04")
    assert no_outcome["status"] == "not_observable"
    assert no_outcome["reason_code"] == "event_after_data_cutoff"
    assert no_outcome["data_cutoff"].startswith("2025-03-04")


def test_daily_and_weekly_methods_are_deterministic(client: TestClient) -> None:
    dataset = daily_dataset(client, days=120)
    signal = create_signal(client, str(dataset["id"]))
    first = estimate(client, str(signal["id"]), frequency="daily")
    second = estimate(client, str(signal["id"]), frequency="daily")
    stable_fields = (
        "baseline_value",
        "observed_value",
        "relative_delta",
        "evidence_score",
        "evidence_level",
        "quality_summary",
    )
    assert all(first[field] == second[field] for field in stable_fields)

    weekly_signal = create_signal(
        client,
        str(dataset["id"]),
        title="Evento semanal",
        event_start="2025-03-05T00:00:00Z",
        event_end="2025-03-11T23:59:59Z",
        signal_type="campaign",
    )
    weekly = estimate(client, str(weekly_signal["id"]), frequency="weekly")
    assert weekly["frequency"] == "weekly"
    assert weekly["method"] == "trailing_8_complete_periods"
    assert weekly["reference_periods"] == 8


def test_scope_specific_series_and_global_series_are_supported(client: TestClient) -> None:
    dataset = daily_dataset(client)
    scopes = [
        {"scope_type": "global", "product": None, "location": None},
        {"scope_type": "product", "product": "A", "location": None},
        {"scope_type": "location", "product": None, "location": "North"},
        {
            "scope_type": "category",
            "product": None,
            "location": None,
            "category": "Core",
        },
    ]
    for index, scope in enumerate(scopes):
        signal = create_signal(
            client, str(dataset["id"]), title=f"Scope {index}", **scope
        )
        result = estimate(client, str(signal["id"]))
        assert result["status"] == "estimated"
        assert result["scope"]["scope_type"] == scope["scope_type"]


def test_historical_analogies_use_only_strict_scope_matches(client: TestClient) -> None:
    dataset = daily_dataset(client, days=150)
    historical_ranges = [
        ("2025-03-05T00:00:00Z", "2025-03-11T23:59:59Z"),
        ("2025-04-02T00:00:00Z", "2025-04-08T23:59:59Z"),
    ]
    for index, (start, end) in enumerate(historical_ranges):
        signal = create_signal(
            client,
            str(dataset["id"]),
            title=f"Histórico {index}",
            event_start=start,
            event_end=end,
            available_at=start,
        )
        assert estimate(client, str(signal["id"]))["status"] == "estimated"

    future = create_signal(
        client,
        str(dataset["id"]),
        title="Promoción futura",
        event_start="2026-01-01T00:00:00Z",
        event_end="2026-01-07T23:59:59Z",
        available_at="2025-06-01T00:00:00Z",
        knowledge_type="known_future",
    )
    analogy = client.get(
        f"/api/v1/context-impact/signals/{future['id']}/analogies"
    ).json()
    assert analogy["status"] == "available"
    assert analogy["comparable_events"] == 2
    assert analogy["median_relative_delta"] is not None

    incompatible = create_signal(
        client,
        str(dataset["id"]),
        title="Scope incompatible",
        event_start="2026-02-01T00:00:00Z",
        event_end="2026-02-07T23:59:59Z",
        available_at="2025-05-01T00:00:00Z",
        knowledge_type="known_future",
        location=None,
    )
    incompatible_analogy = client.get(
        f"/api/v1/context-impact/signals/{incompatible['id']}/analogies"
    ).json()
    assert incompatible_analogy["status"] == "insufficient_evidence"
    assert incompatible_analogy["comparable_events"] == 0


def test_estimate_persists_and_dataset_api_returns_latest_revision(client: TestClient) -> None:
    dataset = daily_dataset(client)
    signal = create_signal(client, str(dataset["id"]))
    first = estimate(client, str(signal["id"]))
    second = estimate(client, str(signal["id"]))

    recovered = client.get(f"/api/v1/context-impact/signals/{signal['id']}")
    assert recovered.status_code == 200
    assert recovered.json()["id"] == second["id"]
    assert first["id"] != second["id"]

    listed = client.get(f"/api/v1/context-impact/datasets/{dataset['id']}")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["estimates"]] == [second["id"]]


def test_context_impact_does_not_modify_series_or_health(client: TestClient) -> None:
    dataset = daily_dataset(client)
    signal = create_signal(client, str(dataset["id"]))
    before = client.get(
        f"/api/v1/series/datasets/{dataset['id']}/profile",
        params={"product": "A", "location": "North", "frequency": "daily"},
    ).json()
    estimate(client, str(signal["id"]))
    after = client.get(
        f"/api/v1/series/datasets/{dataset['id']}/profile",
        params={"product": "A", "location": "North", "frequency": "daily"},
    ).json()
    assert after == before
    assert client.get("/health").status_code == 200


def test_demo_competitor_analogy_survives_deterministic_regeneration(
    client: TestClient,
) -> None:
    dataset = client.post("/api/v1/datasets/demo").json()
    mappings = [
        {"column_name": item["column_name"], "role": item["role"]}
        for item in dataset["mappings"]
    ]
    assert client.put(
        f"/api/v1/datasets/{dataset['id']}/mappings", json={"mappings": mappings}
    ).status_code == 200
    assert client.post(f"/api/v1/datasets/{dataset['id']}/validate").status_code == 200
    assert client.post(f"/api/v1/datasets/{dataset['id']}/ready").status_code == 200
    first = client.post(
        "/api/v1/context-signals/demo/regenerate", json={"dataset_id": dataset["id"]}
    )
    assert first.status_code == 200, first.text
    first_signals = first.json()["signals"]
    historical = next(
        signal
        for signal in first_signals
        if signal["title"] == "Promoción competidora observada"
    )
    planned = next(
        signal
        for signal in first_signals
        if signal["title"] == "Promoción competidora planificada Lima Centro"
    )
    cutoff = "2026-08-30T23:59:59Z"
    assert planned["available_at"] <= cutoff < planned["event_start"]
    assert {
        key: planned[key] for key in ("scope_type", "category", "location")
    } == {
        key: historical[key] for key in ("scope_type", "category", "location")
    }

    visible = client.get(
        "/api/v1/context-signals",
        params={"dataset_id": dataset["id"], "cutoff": cutoff},
    )
    assert visible.status_code == 200
    assert planned["id"] in {signal["id"] for signal in visible.json()}

    impact = estimate(client, str(historical["id"]))
    assert impact["status"] == "estimated"
    assert impact["relative_delta"] < 0
    analogy = client.get(
        f"/api/v1/context-impact/signals/{planned['id']}/analogies"
    ).json()
    assert analogy["status"] == "available"
    assert analogy["comparable_events"] == 1
    assert analogy["minimum_relative_delta"] == analogy["median_relative_delta"]
    assert analogy["median_relative_delta"] == analogy["maximum_relative_delta"]
    assert "no modifica el pronóstico" in analogy["notes"]

    forecasts_before = client.get("/api/v1/forecast-runs").json()
    second = client.post(
        "/api/v1/context-signals/demo/regenerate", json={"dataset_id": dataset["id"]}
    )
    third = client.post(
        "/api/v1/context-signals/demo/regenerate", json={"dataset_id": dataset["id"]}
    )
    assert [signal["id"] for signal in second.json()["signals"]] == [
        signal["id"] for signal in third.json()["signals"]
    ]
    recovered_impact = client.get(
        f"/api/v1/context-impact/signals/{historical['id']}"
    ).json()
    recovered_analogy = client.get(
        f"/api/v1/context-impact/signals/{planned['id']}/analogies"
    ).json()
    assert recovered_impact["id"] == impact["id"]
    assert recovered_analogy["status"] == "available"
    assert recovered_analogy["comparable_events"] == 1
    assert client.get("/api/v1/forecast-runs").json() == forecasts_before
