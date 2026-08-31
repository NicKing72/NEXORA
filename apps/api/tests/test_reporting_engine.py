"""Deterministic coverage for immutable auditable reporting."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from nexora_api.db.base import Base
from nexora_api.db.session import get_database_session
from nexora_api.main import app
from nexora_api.models.dataset import Dataset, ForecastModelResult, ForecastPoint, ForecastRun
from nexora_api.models.decision import DecisionRecommendation, DecisionRun
from nexora_api.models.explanation import ExplanationRun
from nexora_api.models.portfolio import PortfolioRun
from nexora_api.models.scenario import ScenarioRun
from nexora_api.models.scor import ScorAssessmentRun
from nexora_api.schemas.report import ReportRequest
from nexora_api.services.reports.service import create_run, regenerate_demo, serialize_run

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
CUTOFF = datetime(2026, 2, 1, tzinfo=UTC)


@pytest.fixture
def report_db() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False, expire_on_commit=False) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def report_client(report_db: Session) -> TestClient:
    def override_database():
        yield report_db

    app.dependency_overrides[get_database_session] = override_database
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _forecast(db: Session, *, created_at: datetime = CREATED) -> ForecastRun:
    dataset = Dataset(
        id=str(uuid4()),
        original_filename="reporting.csv",
        stored_path="ignored/source.csv",
        canonical_path="ignored/canonical.csv",
        source_type="demo",
        file_type="csv",
        file_size=120,
        sha256="a" * 64,
        row_count=100,
        column_count=4,
        status="ready",
        frequency="weekly",
        readiness_score=92,
        imported_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    run = ForecastRun(
        id=str(uuid4()),
        dataset_id=dataset.id,
        product="NX-101",
        location="Lima Centro",
        category="Bebidas",
        frequency="weekly",
        requested_horizon=4,
        validation_horizon=2,
        created_at=created_at,
        data_cutoff=datetime(2025, 12, 31, tzinfo=UTC),
        preprocessing_summary={"training_cutoff": "2025-12-22"},
        seasonality_candidate=52,
        seasonality_evidence="moderate",
        status="completed",
        champion_model="moving_average",
        champion_reason="lowest_wmape",
        warnings=[],
    )
    db.add_all([dataset, run])
    db.flush()
    db.add(
        ForecastModelResult(
            run_id=run.id,
            model_name="moving_average",
            eligible=True,
            status="succeeded",
            parameters={"window": 4},
            metrics={"wmape": 0.1322, "mae": 4.0},
            stability={"label": "moderate"},
            rank=1,
        )
    )
    for index, value in enumerate([276.75, 276.75, 276.75, 276.75]):
        db.add(
            ForecastPoint(
                run_id=run.id,
                timestamp=datetime(2026, 1, 5, tzinfo=UTC) + timedelta(weeks=index),
                forecast=value,
                lower_80=value - 20,
                upper_80=value + 20,
                lower_95=value - 30,
                upper_95=value + 30,
            )
        )
    db.commit()
    return run


def _layers(db: Session, forecast: ForecastRun) -> dict[str, object]:
    scenario = ScenarioRun(
        id=str(uuid4()),
        forecast_run_id=forecast.id,
        dataset_id=forecast.dataset_id,
        name="Escenario reporte",
        description="Hipótesis",
        status="completed",
        frequency="weekly",
        horizon=4,
        champion_model="moving_average",
        data_cutoff=forecast.data_cutoff,
        selection_json={"product": "NX-101", "location": "Lima Centro"},
        baseline_snapshot={"points": []},
        provenance_json={"official_forecast_modified": False},
        summary_json={"relative_delta": -0.054},
        warnings=[],
        created_at=CREATED + timedelta(days=1),
        executed_at=CREATED + timedelta(days=2),
    )
    scor = ScorAssessmentRun(
        id=str(uuid4()),
        name="SCOR reporte",
        company_name="NEXORA",
        source_dataset_id=forecast.dataset_id,
        forecast_run_id=forecast.id,
        period_start=datetime(2025, 7, 1, tzinfo=UTC),
        period_end=datetime(2025, 12, 31, tzinfo=UTC),
        cutoff=CREATED + timedelta(days=3),
        status="calculated",
        source_name="test",
        source_metadata={},
        summary_json={"metrics_total": 26, "metrics_complete": 22},
        criticality_json={"critical_processes": ["DELIVER"]},
        warnings=[],
        algorithm_version="scor_diagnostic_v1",
        created_at=CREATED + timedelta(days=1),
        calculated_at=CREATED + timedelta(days=2),
    )
    portfolio = PortfolioRun(
        id=str(uuid4()),
        dataset_id=forecast.dataset_id,
        source_mode="official",
        cutoff=CREATED + timedelta(days=3),
        created_at=CREATED + timedelta(days=3),
        available_at=CREATED + timedelta(days=3),
        calculation_version="portfolio_v1",
        forecast_run_ids=[forecast.id],
        filters_json={},
        number_of_series=1,
        summary_json={"series_evaluated": 1},
        warnings=[],
        provenance_json={"forecast_runs_modified": False},
    )
    decision = DecisionRun(
        id=str(uuid4()),
        forecast_run_id=forecast.id,
        scenario_run_id=scenario.id,
        dataset_id=forecast.dataset_id,
        decision_cutoff=CREATED + timedelta(days=4),
        status="completed",
        source_snapshot={
            "scor": {"scor_assessment_id": scor.id},
            "portfolio": {"portfolio_run_id": portfolio.id},
        },
        summary_json={"high_priority_count": 1},
        warnings=[],
        created_at=CREATED + timedelta(days=4),
    )
    decision.recommendations.append(
        DecisionRecommendation(
            id=str(uuid4()),
            rank=1,
            priority="high",
            action_type="monitor",
            title="Revisar distribución",
            summary="Brecha persistida",
            rationale="Evidencia cuantitativa",
            support_score=82,
            evidence_level="high",
            scope_json={},
            dataset_id=forecast.dataset_id,
            product="NX-101",
            location="Lima Centro",
            category="Bebidas",
            forecast_run_id=forecast.id,
            scenario_run_id=scenario.id,
            context_signal_ids=[],
            context_impact_ids=[],
            decision_cutoff=decision.decision_cutoff,
            status="open",
            limitations=["No ejecuta órdenes"],
            provenance_json={},
            created_at=decision.created_at,
            updated_at=decision.created_at,
        )
    )
    explanation = ExplanationRun(
        id=str(uuid4()),
        forecast_run_id=forecast.id,
        dataset_id=forecast.dataset_id,
        series_id="NX-101|Lima Centro",
        frequency="weekly",
        horizon=4,
        champion_model="moving_average",
        cutoff=CREATED + timedelta(days=4),
        version="explanation_v1",
        status="completed",
        created_from="decision",
        source_snapshot={
            "layers": {
                "scenario": {"id": scenario.id},
                "scor": {"id": scor.id},
                "portfolio": {"id": portfolio.id},
                "decision": {"id": decision.id},
            }
        },
        limitations_snapshot=[],
        created_at=CREATED + timedelta(days=5),
        available_at=CREATED + timedelta(days=5),
    )
    db.add_all([scenario, scor, portfolio, decision, explanation])
    db.commit()
    return {
        "scenario": scenario,
        "scor": scor,
        "portfolio": portfolio,
        "decision": decision,
        "explanation": explanation,
    }


def _payload(forecast: ForecastRun, **values: object) -> dict[str, object]:
    return {
        "report_type": "forecast",
        "title": "Reporte de pronóstico NX-101",
        "report_cutoff": CUTOFF.isoformat(),
        "forecast_run_id": forecast.id,
        **values,
    }


def test_report_definitions(report_client: TestClient) -> None:
    response = report_client.get("/api/v1/reports/definitions")
    assert response.status_code == 200
    assert {item["key"] for item in response.json()["report_types"]} == {
        "integrated", "forecast", "decisions", "scor", "portfolio"
    }


def test_forecast_only_preflight_and_create(
    report_client: TestClient, report_db: Session
) -> None:
    forecast = _forecast(report_db)
    preflight = report_client.post("/api/v1/reports/preflight", json=_payload(forecast))
    assert preflight.status_code == 200
    assert preflight.json()["coverage"]["included"] == 1
    assert preflight.json()["sources"]["scenario"]["included"] is False
    created = report_client.post("/api/v1/reports", json=_payload(forecast))
    assert created.status_code == 201
    assert created.json()["source_snapshot"]["forecast"]["recalculated"] is False
    assert created.json()["source_snapshot"]["scenario"] is None


def test_integrated_report_freezes_all_explicit_sources(
    report_client: TestClient, report_db: Session
) -> None:
    forecast = _forecast(report_db)
    layers = _layers(report_db, forecast)
    identifiers = {
        "scenario_run_id": layers["scenario"].id,
        "scor_assessment_id": layers["scor"].id,
        "portfolio_run_id": layers["portfolio"].id,
        "decision_run_id": layers["decision"].id,
        "explanation_run_id": layers["explanation"].id,
    }
    payload = _payload(
        forecast,
        report_type="integrated",
        **identifiers,
    )
    response = report_client.post("/api/v1/reports", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["coverage"]["included"] == 6
    assert body["layer_count"] == 6
    assert len(body["sections"]) == 12


def test_incompatible_scenario_is_rejected(report_client: TestClient, report_db: Session) -> None:
    first = _forecast(report_db)
    second = _forecast(report_db)
    scenario = _layers(report_db, second)["scenario"]
    response = report_client.post(
        "/api/v1/reports/preflight",
        json=_payload(first, report_type="integrated", scenario_run_id=scenario.id),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "report_source_incompatible"


def test_unknown_uuid_is_rejected_without_fallback(report_client: TestClient) -> None:
    response = report_client.post(
        "/api/v1/reports/preflight",
        json={
            "report_type": "forecast",
            "title": "Reporte desconocido",
            "report_cutoff": CUTOFF.isoformat(),
            "forecast_run_id": str(uuid4()),
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "report_forecast_not_found"


def test_invalid_uuid_contract_returns_422(report_client: TestClient) -> None:
    response = report_client.post(
        "/api/v1/reports/preflight",
        json={
            "report_type": "forecast",
            "title": "Reporte inválido",
            "report_cutoff": CUTOFF.isoformat(),
            "forecast_run_id": "not-a-uuid",
        },
    )
    assert response.status_code == 422


def test_future_evidence_is_blocked(report_client: TestClient, report_db: Session) -> None:
    forecast = _forecast(report_db, created_at=CUTOFF + timedelta(days=1))
    response = report_client.post("/api/v1/reports/preflight", json=_payload(forecast))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "report_temporal_leakage_blocked"


def test_snapshot_is_immutable_after_source_changes(report_db: Session) -> None:
    forecast = _forecast(report_db)
    request = ReportRequest(**_payload(forecast))
    run = create_run(report_db, request)
    before = deepcopy(run.source_snapshot)
    forecast.champion_model = "naive"
    forecast.points[0].forecast = 9999
    report_db.commit()
    report_db.refresh(run)
    assert run.source_snapshot == before
    assert run.source_snapshot["forecast"]["champion_model"] == "moving_average"


def test_multiple_reports_do_not_collide(report_db: Session) -> None:
    forecast = _forecast(report_db)
    request = ReportRequest(**_payload(forecast))
    first = create_run(report_db, request)
    second = create_run(report_db, request)
    assert first.id != second.id


@pytest.mark.parametrize("format", ["json", "html", "csv"])
def test_exports_are_reproducible(
    report_client: TestClient, report_db: Session, format: str
) -> None:
    forecast = _forecast(report_db)
    run = create_run(report_db, ReportRequest(**_payload(forecast)))
    response = report_client.get(f"/api/v1/reports/{run.id}/export?format={format}")
    assert response.status_code == 200
    assert run.id in response.text
    if format == "csv":
        assert "section,record,key,value,status,source_id" in response.text


def test_demo_is_decoupled_and_deterministic(report_db: Session) -> None:
    first = regenerate_demo(report_db)
    first_payload = deepcopy(first.report_payload)
    second = regenerate_demo(report_db)
    assert first.id == second.id
    assert second.is_demo is True
    assert second.report_payload == first_payload
    assert second.forecast_run_id is None


def test_demo_api_marks_report_visibly(report_client: TestClient) -> None:
    response = report_client.post("/api/v1/reports/demo/regenerate")
    assert response.status_code == 200
    assert response.json()["is_demo"] is True
    assert response.json()["title"].startswith("DEMO")


def test_missing_values_are_not_serialized_as_zero(report_db: Session) -> None:
    forecast = _forecast(report_db)
    forecast.points[0].lower_95 = None
    report_db.commit()
    run = create_run(report_db, ReportRequest(**_payload(forecast)))
    assert run.source_snapshot["forecast"]["forecast_points"][0]["lower_95"] is None


def test_sections_sources_and_summary_endpoints(
    report_client: TestClient, report_db: Session
) -> None:
    forecast = _forecast(report_db)
    run = create_run(report_db, ReportRequest(**_payload(forecast)))
    assert report_client.get(f"/api/v1/reports/{run.id}/sections").status_code == 200
    sources = report_client.get(f"/api/v1/reports/{run.id}/sources").json()
    assert sources["provenance"]["sources_recalculated"] is False
    summary = report_client.get(f"/api/v1/reports/{run.id}/summary").json()
    assert summary["executive_summary"]["causal_claims"] is False


def test_historical_recovery_uses_exact_id(report_client: TestClient, report_db: Session) -> None:
    forecast = _forecast(report_db)
    first = create_run(report_db, ReportRequest(**_payload(forecast)))
    second = create_run(report_db, ReportRequest(**_payload(forecast, title="Otro reporte")))
    recovered = report_client.get(f"/api/v1/reports/{first.id}").json()
    assert recovered["id"] == first.id
    assert recovered["id"] != second.id


def test_report_creation_does_not_mutate_forecast(report_db: Session) -> None:
    forecast = _forecast(report_db)
    before = {
        "champion": forecast.champion_model,
        "points": [item.forecast for item in forecast.points],
    }
    create_run(report_db, ReportRequest(**_payload(forecast)))
    report_db.refresh(forecast)
    assert forecast.champion_model == before["champion"]
    assert [item.forecast for item in forecast.points] == before["points"]


def test_required_source_depends_on_report_type(report_client: TestClient) -> None:
    response = report_client.post(
        "/api/v1/reports/preflight",
        json={
            "report_type": "decisions",
            "title": "Reporte decisiones",
            "report_cutoff": CUTOFF.isoformat(),
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "report_required_source_missing"


def test_report_serialization_contains_version_and_provenance(report_db: Session) -> None:
    forecast = _forecast(report_db)
    run = create_run(report_db, ReportRequest(**_payload(forecast)))
    body = serialize_run(run)
    assert body["calculation_version"] == "reporting_engine_v1"
    assert body["report_payload"]["snapshot_immutable"] is True
    assert body["report_payload"]["sources_recalculated"] is False
