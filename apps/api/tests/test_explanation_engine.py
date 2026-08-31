"""Deterministic coverage for immutable forecast explanations."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from nexora_api.core.exceptions import DataStudioError
from nexora_api.db.base import Base
from nexora_api.db.session import get_database_session
from nexora_api.main import app
from nexora_api.models.dataset import (
    Dataset,
    ForecastFoldResult,
    ForecastModelResult,
    ForecastPoint,
    ForecastRun,
)
from nexora_api.models.decision import DecisionRun
from nexora_api.models.explanation import ExplanationRun
from nexora_api.models.portfolio import PortfolioRun
from nexora_api.models.scenario import ScenarioRun
from nexora_api.models.scor import ScorAssessmentRun
from nexora_api.services.explanations.comparison import comparison_snapshot
from nexora_api.services.explanations.forecast_explanation import forecast_snapshot
from nexora_api.services.explanations.model_explanation import (
    list_definitions,
    require_definition,
)
from nexora_api.services.explanations.service import (
    create_run,
    require_run,
    serialize_run,
)

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
CUTOFF = datetime(2026, 1, 10, tzinfo=UTC)


@pytest.fixture
def explanation_db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False, expire_on_commit=False) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def explanation_client(explanation_db: Session) -> TestClient:
    def override_database():
        yield explanation_db

    app.dependency_overrides[get_database_session] = override_database
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _forecast(db: Session, *, parameters: dict[str, object] | None = None) -> ForecastRun:
    dataset_id = str(uuid4())
    run_id = str(uuid4())
    db.add(
        Dataset(
            id=dataset_id,
            original_filename="explanation.csv",
            stored_path="ignored/source.csv",
            canonical_path="ignored/canonical.csv",
            source_type="demo",
            file_type="csv",
            file_size=100,
            sha256="a" * 64,
            row_count=104,
            column_count=4,
            status="ready",
            frequency="weekly",
            readiness_score=91,
            imported_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
    )
    run = ForecastRun(
        id=run_id,
        dataset_id=dataset_id,
        product="NX-101",
        location="Lima Centro",
        category="Bebidas",
        frequency="weekly",
        requested_horizon=12,
        validation_horizon=2,
        created_at=CREATED,
        data_cutoff=datetime(2025, 12, 31, tzinfo=UTC),
        preprocessing_summary={
            "training_cutoff": "2025-12-22",
            "training_periods": 104,
            "missing_before": 0,
            "excluded_partial_periods": 1,
            "interval_method": "pooled_out_of_sample_residual_quantiles",
            "interval_residual_count": 10,
        },
        seasonality_candidate=52,
        seasonality_evidence="moderate",
        status="completed",
        champion_model="moving_average",
        champion_reason="lowest_wmape",
        warnings=[],
    )
    db.add(run)
    champion = ForecastModelResult(
        run_id=run_id,
        model_name="moving_average",
        eligible=True,
        status="succeeded",
        parameters={"window": 4, "engine": "native_baseline"}
        if parameters is None
        else parameters,
        metrics={
            "observations": 10,
            "mae": 2.1,
            "rmse": 2.8,
            "mape": 0.08,
            "smape": 0.081,
            "wmape": 0.082,
            "bias": -0.3,
            "bias_percent": -0.01,
        },
        stability={"label": "high", "wmape_cv": 0.05},
        rank=1,
    )
    runner_up = ForecastModelResult(
        run_id=run_id,
        model_name="naive",
        eligible=True,
        status="succeeded",
        parameters={"strategy": "last_value"},
        metrics={"observations": 10, "mae": 2.2, "rmse": 3.0, "wmape": 0.085},
        stability={"label": "moderate", "wmape_cv": 0.12},
        rank=2,
    )
    db.add_all([champion, runner_up])
    db.flush()
    for index in range(5):
        db.add(
            ForecastFoldResult(
                model_result_id=champion.id,
                fold_index=index + 1,
                train_start=datetime(2024, 1, 1, tzinfo=UTC),
                train_end=datetime(2025, 11, 1, tzinfo=UTC) + timedelta(days=7 * index),
                validation_start=datetime(2025, 11, 8, tzinfo=UTC)
                + timedelta(days=7 * index),
                validation_end=datetime(2025, 11, 15, tzinfo=UTC)
                + timedelta(days=7 * index),
                training_observations=80 + index,
                validation_observations=2,
                metrics={"wmape": 0.08 + index * 0.001, "mae": 2.0},
                actual_values=[100.0, 110.0],
                forecast_values=[98.0, 108.0],
            )
        )
    for index in range(12):
        value = 276.75 + index
        db.add(
            ForecastPoint(
                run_id=run_id,
                timestamp=datetime(2026, 1, 5, tzinfo=UTC) + timedelta(days=7 * index),
                forecast=value,
                lower_80=value - 10,
                upper_80=value + 10,
                lower_95=value - 20,
                upper_95=value + 20,
            )
        )
    db.commit()
    return run


def _request(run: ForecastRun, **overrides: object) -> dict[str, object]:
    return {
        "forecast_run_id": run.id,
        "cutoff": CUTOFF,
        "scenario_run_id": None,
        "scor_assessment_id": None,
        "portfolio_run_id": None,
        "decision_run_id": None,
        **overrides,
    }


def test_catalog_covers_exact_supported_models() -> None:
    assert {item["key"] for item in list_definitions()} == {
        "naive",
        "seasonal_naive",
        "moving_average",
        "ses",
        "holt",
        "holt_winters_additive",
        "holt_winters_multiplicative",
    }


def test_unknown_model_definition_is_rejected() -> None:
    with pytest.raises(DataStudioError) as error:
        require_definition("invented_model")
    assert error.value.code == "explanation_model_not_found"


def test_persisted_ranking_and_near_tie_are_reconstructed_not_rewritten(
    explanation_db: Session,
) -> None:
    run = _forecast(explanation_db)
    rows = comparison_snapshot(run)
    assert [row["model_name"] for row in rows] == ["moving_average", "naive"]
    assert [row["rank"] for row in rows] == [1, 2]
    assert rows[1]["within_champion_tolerance"] is True


def test_forecast_snapshot_includes_intervals_and_deterministic_trend(
    explanation_db: Session,
) -> None:
    result = forecast_snapshot(_forecast(explanation_db))
    assert result["summary"]["period_count"] == 12
    assert result["summary"]["trend"]["label"] == "increasing"
    assert result["summary"]["average_width_80"] == 20
    assert result["summary"]["average_width_95"] == 40


def test_explanation_persists_champion_five_folds_and_provenance(
    explanation_db: Session,
) -> None:
    forecast = _forecast(explanation_db)
    result = serialize_run(create_run(explanation_db, **_request(forecast)))
    snapshot = result["source_snapshot"]
    assert result["champion_model"] == "moving_average"
    assert snapshot["backtesting"]["summary"]["fold_count"] == 5
    assert snapshot["forecast_output"]["summary"]["horizon"] == 12
    assert snapshot["provenance"]["forecast_core_version"] is None
    assert not any(snapshot["layers"].values())
    assert all(item["provenance"]["recalculated"] is False for item in result["evidence"])
    assert len(result["evidence"]) == 7


def test_missing_parameters_are_declared_not_invented(explanation_db: Session) -> None:
    forecast = _forecast(explanation_db, parameters={})
    result = serialize_run(create_run(explanation_db, **_request(forecast)))
    assert "model_parameters_not_persisted" in result["limitations"]
    assert result["source_snapshot"]["champion"]["explanation"]["parameters"] == {}


def test_forecast_after_explanation_cutoff_is_rejected(explanation_db: Session) -> None:
    forecast = _forecast(explanation_db)
    with pytest.raises(DataStudioError) as error:
        create_run(
            explanation_db,
            **_request(forecast, cutoff=CREATED - timedelta(seconds=1)),
        )
    assert error.value.code == "explanation_future_forecast"


def test_historical_explanation_snapshot_is_immutable(explanation_db: Session) -> None:
    forecast = _forecast(explanation_db)
    explanation = create_run(explanation_db, **_request(forecast))
    frozen = deepcopy(explanation.source_snapshot)
    champion = next(model for model in forecast.model_results if model.rank == 1)
    champion.metrics = {**champion.metrics, "wmape": 0.999}
    explanation_db.commit()
    assert require_run(explanation_db, explanation.id).source_snapshot == frozen


def test_optional_layers_remain_separate_and_temporally_valid(explanation_db: Session) -> None:
    forecast = _forecast(explanation_db)
    scenario_id, scor_id, portfolio_id, decision_id = (str(uuid4()) for _ in range(4))
    explanation_db.add(
        ScenarioRun(
            id=scenario_id,
            forecast_run_id=forecast.id,
            dataset_id=forecast.dataset_id,
            name="Escenario",
            status="completed",
            frequency="weekly",
            horizon=12,
            champion_model="moving_average",
            data_cutoff=forecast.data_cutoff,
            created_at=CREATED + timedelta(days=1),
            executed_at=CREATED + timedelta(days=1),
        )
    )
    explanation_db.add(
        ScorAssessmentRun(
            id=scor_id,
            name="SCOR",
            source_dataset_id=forecast.dataset_id,
            forecast_run_id=forecast.id,
            period_start=datetime(2025, 7, 1, tzinfo=UTC),
            period_end=datetime(2025, 12, 31, tzinfo=UTC),
            cutoff=datetime(2025, 12, 31, tzinfo=UTC),
            status="calculated",
            source_name="manual",
            algorithm_version="scor_diagnostic_v1",
            created_at=CREATED + timedelta(days=1),
            calculated_at=CREATED + timedelta(days=1),
        )
    )
    explanation_db.add(
        PortfolioRun(
            id=portfolio_id,
            dataset_id=forecast.dataset_id,
            source_mode="official",
            cutoff=datetime(2025, 12, 31, tzinfo=UTC),
            created_at=CREATED + timedelta(days=1),
            available_at=CREATED + timedelta(days=1),
            calculation_version="portfolio_engine_v1",
            forecast_run_ids=[forecast.id],
        )
    )
    explanation_db.add(
        DecisionRun(
            id=decision_id,
            forecast_run_id=forecast.id,
            dataset_id=forecast.dataset_id,
            decision_cutoff=CREATED + timedelta(days=1),
            source_snapshot={
                "context": {"signals": ["signal-1"]},
                "portfolio": {"portfolio_run_id": portfolio_id},
            },
            created_at=CREATED + timedelta(days=1),
        )
    )
    explanation_db.commit()
    result = serialize_run(
        create_run(
            explanation_db,
            **_request(
                forecast,
                scenario_run_id=scenario_id,
                scor_assessment_id=scor_id,
                portfolio_run_id=portfolio_id,
                decision_run_id=decision_id,
            ),
        )
    )
    layers = result["source_snapshot"]["layers"]
    assert layers["scenario"]["hypothetical"] is True
    assert layers["scor"]["id"] == scor_id
    assert layers["portfolio"]["id"] == portfolio_id
    assert layers["decision"]["id"] == decision_id
    assert layers["context"] == {"signals": ["signal-1"]}


def test_decision_layers_without_portfolio_remain_absent(explanation_db: Session) -> None:
    forecast = _forecast(explanation_db)
    scenario_id, scor_id, decision_id = (str(uuid4()) for _ in range(3))
    explanation_db.add(
        ScenarioRun(
            id=scenario_id,
            forecast_run_id=forecast.id,
            dataset_id=forecast.dataset_id,
            name="Escenario sin portafolio",
            status="completed",
            frequency="weekly",
            horizon=12,
            champion_model="moving_average",
            data_cutoff=forecast.data_cutoff,
            created_at=CREATED + timedelta(days=1),
            executed_at=CREATED + timedelta(days=1),
        )
    )
    explanation_db.add(
        ScorAssessmentRun(
            id=scor_id,
            name="SCOR sin portafolio",
            source_dataset_id=forecast.dataset_id,
            forecast_run_id=forecast.id,
            period_start=datetime(2025, 7, 1, tzinfo=UTC),
            period_end=datetime(2025, 12, 31, tzinfo=UTC),
            cutoff=datetime(2025, 12, 31, tzinfo=UTC),
            status="calculated",
            source_name="manual",
            algorithm_version="scor_diagnostic_v1",
            created_at=CREATED + timedelta(days=1),
            calculated_at=CREATED + timedelta(days=1),
        )
    )
    explanation_db.add(
        DecisionRun(
            id=decision_id,
            forecast_run_id=forecast.id,
            scenario_run_id=scenario_id,
            dataset_id=forecast.dataset_id,
            decision_cutoff=CREATED + timedelta(days=1),
            source_snapshot={
                "scor": {"scor_assessment_id": scor_id},
                "portfolio": None,
            },
            created_at=CREATED + timedelta(days=1),
        )
    )
    explanation_db.commit()

    result = serialize_run(
        create_run(
            explanation_db,
            **_request(
                forecast,
                scenario_run_id=scenario_id,
                scor_assessment_id=scor_id,
                decision_run_id=decision_id,
            ),
        )
    )

    layers = result["source_snapshot"]["layers"]
    assert [key for key in ("scenario", "scor", "portfolio", "decision") if layers[key]] == [
        "scenario",
        "scor",
        "decision",
    ]


def test_decision_rejects_unassociated_compatible_portfolio_without_fallback(
    explanation_db: Session,
) -> None:
    forecast = _forecast(explanation_db)
    associated_id, unrelated_id, decision_id = (str(uuid4()) for _ in range(3))
    for portfolio_id in (associated_id, unrelated_id):
        explanation_db.add(
            PortfolioRun(
                id=portfolio_id,
                dataset_id=forecast.dataset_id,
                source_mode="official",
                cutoff=datetime(2025, 12, 31, tzinfo=UTC),
                created_at=CREATED + timedelta(days=1),
                available_at=CREATED + timedelta(days=1),
                calculation_version="portfolio_engine_v1",
                forecast_run_ids=[forecast.id],
            )
        )
    explanation_db.add(
        DecisionRun(
            id=decision_id,
            forecast_run_id=forecast.id,
            dataset_id=forecast.dataset_id,
            decision_cutoff=CREATED + timedelta(days=1),
            source_snapshot={"portfolio": {"portfolio_run_id": associated_id}},
            created_at=CREATED + timedelta(days=1),
        )
    )
    explanation_db.commit()

    with pytest.raises(DataStudioError) as error:
        create_run(
            explanation_db,
            **_request(
                forecast,
                portfolio_run_id=unrelated_id,
                decision_run_id=decision_id,
            ),
        )

    assert error.value.code == "explanation_source_mismatch"
    assert explanation_db.query(ExplanationRun).count() == 0


def test_future_portfolio_cannot_leak_into_explanation(explanation_db: Session) -> None:
    forecast = _forecast(explanation_db)
    portfolio = PortfolioRun(
        id=str(uuid4()),
        dataset_id=forecast.dataset_id,
        source_mode="official",
        cutoff=datetime(2025, 12, 31, tzinfo=UTC),
        created_at=CUTOFF + timedelta(seconds=1),
        available_at=CUTOFF + timedelta(seconds=1),
        calculation_version="portfolio_engine_v1",
        forecast_run_ids=[forecast.id],
    )
    explanation_db.add(portfolio)
    explanation_db.commit()
    with pytest.raises(DataStudioError) as error:
        create_run(
            explanation_db,
            **_request(forecast, portfolio_run_id=portfolio.id),
        )
    assert error.value.code == "explanation_future_source"


def test_creating_explanation_does_not_mutate_forecast(explanation_db: Session) -> None:
    forecast = _forecast(explanation_db)
    before = {
        "champion": forecast.champion_model,
        "points": [(point.timestamp, point.forecast) for point in forecast.points],
        "models": [
            (model.model_name, model.rank, deepcopy(model.metrics))
            for model in forecast.model_results
        ],
    }
    create_run(explanation_db, **_request(forecast))
    explanation_db.refresh(forecast)
    after = {
        "champion": forecast.champion_model,
        "points": [(point.timestamp, point.forecast) for point in forecast.points],
        "models": [
            (model.model_name, model.rank, deepcopy(model.metrics))
            for model in forecast.model_results
        ],
    }
    assert after == before


def test_api_preflight_creation_recovery_and_views(
    explanation_client: TestClient, explanation_db: Session
) -> None:
    forecast = _forecast(explanation_db)
    payload = {"forecast_run_id": forecast.id, "cutoff": CUTOFF.isoformat()}
    preflight = explanation_client.post("/api/v1/explanations/preflight", json=payload)
    assert preflight.status_code == 200, preflight.text
    created = explanation_client.post("/api/v1/explanations", json=payload)
    assert created.status_code == 201, created.text
    run_id = created.json()["id"]
    assert explanation_client.get("/api/v1/explanations/definitions").status_code == 200
    assert explanation_client.get("/api/v1/explanations").status_code == 200
    assert explanation_client.get(f"/api/v1/explanations/{run_id}").json() == created.json()
    for suffix in ("evidence", "models", "backtesting", "forecast", "provenance"):
        response = explanation_client.get(f"/api/v1/explanations/{run_id}/{suffix}")
        assert response.status_code == 200, response.text


def test_health_remains_operational(explanation_client: TestClient) -> None:
    assert explanation_client.get("/health").status_code == 200
