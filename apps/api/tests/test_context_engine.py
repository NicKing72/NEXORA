"""Deterministic coverage for Context Engine contracts, matching, and temporal safety."""

from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient


def signal_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "signal_family": "commercial",
        "signal_type": "price_change",
        "title": "Cambio de precio confirmado",
        "description": "Una señal manual para pruebas.",
        "event_start": "2026-05-01T00:00:00Z",
        "event_end": "2026-05-02T00:00:00Z",
        "observed_at": "2026-05-03T08:00:00Z",
        "available_at": "2026-05-03T09:00:00Z",
        "knowledge_type": "observed",
        "scope_type": "global",
        "confidence": 0.8,
        "source_reference": "Nota interna CONTEXT-01",
        "metadata": {"owner": "commercial"},
    }
    payload.update(overrides)
    return payload


def create_signal(client: TestClient, **overrides: object) -> dict[str, object]:
    response = client.post("/api/v1/context-signals", json=signal_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def test_creates_manual_signal_with_owned_provenance(client: TestClient) -> None:
    signal = create_signal(client)

    assert signal["source_type"] == "manual"
    assert signal["source_name"] == "usuario/manual"
    assert signal["status"] == "confirmed"
    assert signal["impact_status"] == "not_estimated"
    assert signal["metadata"] == {"owner": "commercial"}


def test_rejects_invalid_dataset_uuid(client: TestClient) -> None:
    response = client.post(
        "/api/v1/context-signals", json=signal_payload(dataset_id="not-a-uuid")
    )
    assert response.status_code == 422


def test_confidence_bounds_are_validated(client: TestClient) -> None:
    assert client.post(
        "/api/v1/context-signals", json=signal_payload(confidence=0.0)
    ).status_code == 201
    assert client.post(
        "/api/v1/context-signals", json=signal_payload(confidence=1.0)
    ).status_code == 201
    assert client.post(
        "/api/v1/context-signals", json=signal_payload(confidence=1.01)
    ).status_code == 422
    assert client.post(
        "/api/v1/context-signals", json=signal_payload(confidence=-0.01)
    ).status_code == 422


def test_rejects_invalid_event_range(client: TestClient) -> None:
    response = client.post(
        "/api/v1/context-signals",
        json=signal_payload(
            event_start="2026-05-03T00:00:00Z", event_end="2026-05-02T00:00:00Z"
        ),
    )
    assert response.status_code == 422


def test_accepts_all_knowledge_types(client: TestClient) -> None:
    for knowledge_type in ("observed", "known_future", "forecasted_external", "scenario"):
        response = client.post(
            "/api/v1/context-signals",
            json=signal_payload(title=f"Signal {knowledge_type}", knowledge_type=knowledge_type),
        )
        assert response.status_code == 201, response.text
        assert response.json()["knowledge_type"] == knowledge_type


def test_status_lifecycle_preserves_signal(client: TestClient) -> None:
    signal = create_signal(client)
    dismissed = client.patch(
        f"/api/v1/context-signals/{signal['id']}/status", json={"status": "dismissed"}
    )
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "dismissed"
    reviewed = client.patch(
        f"/api/v1/context-signals/{signal['id']}/status", json={"status": "reviewed"}
    )
    assert reviewed.status_code == 200
    assert client.get(f"/api/v1/context-signals/{signal['id']}").status_code == 200


def test_rejects_invalid_status_transition(client: TestClient) -> None:
    signal = create_signal(client)
    expired = client.patch(
        f"/api/v1/context-signals/{signal['id']}/status", json={"status": "expired"}
    )
    assert expired.status_code == 200
    rejected = client.patch(
        f"/api/v1/context-signals/{signal['id']}/status", json={"status": "confirmed"}
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "invalid_status_transition"


def test_global_scope_matches_any_series(client: TestClient) -> None:
    signal = create_signal(client)
    matches = client.get(
        "/api/v1/context-signals/relevant",
        params={"product": "NX-999", "location": "Cusco"},
    ).json()
    assert [item["signal"]["id"] for item in matches] == [signal["id"]]
    assert matches[0]["match_reasons"][0]["dimension"] == "scope"


def test_product_location_and_category_scopes_match(client: TestClient) -> None:
    product = create_signal(
        client, title="Producto", scope_type="product", product="NX-101"
    )
    location = create_signal(
        client, title="Ubicación", scope_type="location", location="Lima Centro"
    )
    category = create_signal(
        client, title="Categoría", scope_type="category", category="Essentials"
    )
    matches = client.get(
        "/api/v1/context-signals/relevant",
        params={
            "product": "NX-101",
            "location": "Lima Centro",
            "category": "Essentials",
        },
    ).json()
    assert {item["signal"]["id"] for item in matches} == {
        product["id"],
        location["id"],
        category["id"],
    }


def test_multiple_explicit_dimensions_must_all_match(client: TestClient) -> None:
    signal = create_signal(
        client,
        scope_type="product",
        product="NX-101",
        location="Lima Centro",
        category="Essentials",
    )
    included = client.get(
        "/api/v1/context-signals/relevant",
        params={
            "product": "NX-101",
            "location": "Lima Centro",
            "category": "Essentials",
        },
    ).json()
    excluded = client.get(
        "/api/v1/context-signals/relevant",
        params={
            "product": "NX-101",
            "location": "Arequipa Norte",
            "category": "Essentials",
        },
    ).json()
    assert included[0]["signal"]["id"] == signal["id"]
    assert {reason["dimension"] for reason in included[0]["match_reasons"]} == {
        "product",
        "category",
        "location",
    }
    assert excluded == []


def test_availability_cutoff_is_independent_from_event_start(client: TestClient) -> None:
    signal = create_signal(
        client,
        event_start="2026-05-01T00:00:00Z",
        event_end=None,
        available_at="2026-05-03T09:00:00Z",
    )
    before = client.get(
        "/api/v1/context-signals/available", params={"cutoff": "2026-05-02T23:59:59Z"}
    )
    after = client.get(
        "/api/v1/context-signals/available", params={"cutoff": "2026-05-04T00:00:00Z"}
    )
    assert before.status_code == 200
    assert before.json() == []
    assert [item["id"] for item in after.json()] == [signal["id"]]


def test_relevance_cutoff_excludes_future_information(client: TestClient) -> None:
    create_signal(client, available_at="2026-06-02T10:00:00Z")
    response = client.get(
        "/api/v1/context-signals/relevant", params={"cutoff": "2026-06-01T23:59:59Z"}
    )
    assert response.status_code == 200
    assert response.json() == []


def test_list_filters_period_family_status_and_source(client: TestClient) -> None:
    signal = create_signal(client)
    create_signal(
        client,
        signal_family="event",
        signal_type="local_event",
        title="Otro evento",
        event_start="2026-08-01T00:00:00Z",
        event_end="2026-08-02T00:00:00Z",
    )
    response = client.get(
        "/api/v1/context-signals",
        params={
            "signal_family": "commercial",
            "status": "confirmed",
            "source_type": "manual",
            "event_from": "2026-04-30T00:00:00Z",
            "event_to": "2026-05-31T23:59:59Z",
        },
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [signal["id"]]


def test_detail_update_and_uuid_validation(client: TestClient) -> None:
    signal = create_signal(client)
    detail = client.get(f"/api/v1/context-signals/{signal['id']}")
    assert detail.status_code == 200
    updated = client.patch(
        f"/api/v1/context-signals/{signal['id']}",
        json={"title": "Precio revisado", "confidence": 0.93},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Precio revisado"
    assert updated.json()["confidence"] == 0.93
    assert client.get("/api/v1/context-signals/not-a-uuid").status_code == 422


def test_update_revalidates_combined_date_range(client: TestClient) -> None:
    signal = create_signal(client)
    response = client.patch(
        f"/api/v1/context-signals/{signal['id']}",
        json={"event_start": "2026-05-04T00:00:00Z"},
    )
    assert response.status_code == 422


def test_demo_context_is_reproducible_and_complete(client: TestClient) -> None:
    dataset = client.post("/api/v1/datasets/demo").json()
    first = client.post(
        "/api/v1/context-signals/demo/regenerate", json={"dataset_id": dataset["id"]}
    )
    second = client.post(
        "/api/v1/context-signals/demo/regenerate", json={"dataset_id": dataset["id"]}
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    first_signals = first.json()["signals"]
    second_signals = second.json()["signals"]
    assert first.json()["generated"] == 9
    assert [signal["id"] for signal in first_signals] == [
        signal["id"] for signal in second_signals
    ]
    assert {signal["knowledge_type"] for signal in first_signals} == {
        "observed",
        "known_future",
        "forecasted_external",
        "scenario",
    }
    assert {signal["signal_type"] for signal in first_signals} >= {
        "own_promotion",
        "competitor_promotion",
        "holiday",
        "local_event",
        "stockout",
        "supplier_delay",
        "price_change",
    }
    holiday = next(signal for signal in first_signals if signal["signal_type"] == "holiday")
    assert holiday["event_start"] == "2026-12-25T05:00:00+00:00"


def test_demo_regeneration_does_not_remove_manual_signal(client: TestClient) -> None:
    dataset = client.post("/api/v1/datasets/demo").json()
    manual = create_signal(client, dataset_id=dataset["id"])
    client.post("/api/v1/context-signals/demo/regenerate", json={"dataset_id": dataset["id"]})
    client.post("/api/v1/context-signals/demo/regenerate", json={"dataset_id": dataset["id"]})
    listed = client.get(
        "/api/v1/context-signals", params={"dataset_id": dataset["id"]}
    ).json()
    assert manual["id"] in {signal["id"] for signal in listed}
    assert len(listed) == 10


def test_demo_context_rejects_non_demo_dataset(client: TestClient) -> None:
    uploaded = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("tiny.csv", b"date,demand\n2026-01-01,1\n", "text/csv")},
    ).json()
    response = client.post(
        "/api/v1/context-signals/demo/regenerate", json={"dataset_id": uploaded["id"]}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "demo_context_requires_demo_dataset"


def test_context_operations_do_not_modify_dataset_metadata(client: TestClient) -> None:
    dataset = client.post("/api/v1/datasets/demo").json()
    before = deepcopy(client.get(f"/api/v1/datasets/{dataset['id']}").json())
    create_signal(client, dataset_id=dataset["id"])
    client.post("/api/v1/context-signals/demo/regenerate", json={"dataset_id": dataset["id"]})
    after = client.get(f"/api/v1/datasets/{dataset['id']}").json()
    assert after == before


def test_health_remains_operational_with_context_routes(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
