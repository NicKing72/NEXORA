"""Smoke tests for the API foundation."""

from fastapi.testclient import TestClient

from nexora_api.main import app


def test_health_returns_operational_status() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "NEXORA API",
        "version": "0.1.0",
        "environment": "development",
    }


def test_openapi_document_exposes_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]
