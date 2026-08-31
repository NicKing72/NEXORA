"""Resolve explicit report sources and enforce compatibility and temporal safety."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import ForecastModelResult, ForecastRun
from nexora_api.models.decision import DecisionRecommendation, DecisionRun
from nexora_api.services.explanations.service import require_run as require_explanation
from nexora_api.services.portfolio.service import require_portfolio
from nexora_api.services.scenarios.service import require_scenario
from nexora_api.services.scor.service import require_assessment


def _error(code: str, message: str, status: int = 409) -> DataStudioError:
    return DataStudioError(code, message, status)


def _require_forecast(db: Session, run_id: str) -> ForecastRun:
    run = (
        db.query(ForecastRun)
        .options(
            selectinload(ForecastRun.points),
            selectinload(ForecastRun.model_results).selectinload(ForecastModelResult.folds),
        )
        .filter(ForecastRun.id == run_id)
        .one_or_none()
    )
    if run is None:
        raise _error("report_forecast_not_found", "El Forecast Run no existe.", 404)
    return run


def _require_decision(db: Session, run_id: str) -> DecisionRun:
    run = (
        db.query(DecisionRun)
        .options(
            selectinload(DecisionRun.recommendations).selectinload(DecisionRecommendation.evidence),
            selectinload(DecisionRun.recommendations).selectinload(
                DecisionRecommendation.audit_entries
            ),
        )
        .filter(DecisionRun.id == run_id)
        .one_or_none()
    )
    if run is None:
        raise _error("report_decision_not_found", "El Decision Run no existe.", 404)
    return run


def _ensure_time(label: str, values: list[datetime | None], cutoff: datetime) -> None:
    if any(value is not None and value > cutoff for value in values):
        raise _error(
            "report_temporal_leakage_blocked",
            f"{label} contiene evidencia posterior al corte del reporte.",
        )


def _layer_id(snapshot: dict[str, object], key: str) -> str | None:
    layers = snapshot.get("layers")
    if not isinstance(layers, dict) or not isinstance(layers.get(key), dict):
        return None
    value = layers[key].get("id")
    return str(value) if value else None


def resolve_sources(
    db: Session,
    *,
    report_type: str,
    report_cutoff: datetime,
    forecast_run_id: str | None,
    scenario_run_id: str | None,
    scor_assessment_id: str | None,
    portfolio_run_id: str | None,
    decision_run_id: str | None,
    explanation_run_id: str | None,
) -> dict[str, object | None]:
    required = {
        "integrated": ("forecast",),
        "forecast": ("forecast",),
        "decisions": ("forecast", "decision"),
        "scor": ("scor",),
        "portfolio": ("portfolio",),
    }[report_type]
    supplied = {
        "forecast": forecast_run_id,
        "scenario": scenario_run_id,
        "scor": scor_assessment_id,
        "portfolio": portfolio_run_id,
        "decision": decision_run_id,
        "explanation": explanation_run_id,
    }
    missing = [key for key in required if not supplied[key]]
    if missing:
        raise _error(
            "report_required_source_missing",
            f"Falta una fuente obligatoria para este reporte: {', '.join(missing)}.",
            422,
        )

    forecast = _require_forecast(db, forecast_run_id) if forecast_run_id else None
    scenario = require_scenario(db, scenario_run_id) if scenario_run_id else None
    scor = require_assessment(db, scor_assessment_id) if scor_assessment_id else None
    portfolio = require_portfolio(db, portfolio_run_id) if portfolio_run_id else None
    decision = _require_decision(db, decision_run_id) if decision_run_id else None
    explanation = require_explanation(db, explanation_run_id) if explanation_run_id else None

    if forecast:
        _ensure_time("Forecast", [forecast.created_at, forecast.data_cutoff], report_cutoff)
        if forecast.status != "completed":
            raise _error("report_forecast_incomplete", "El Forecast Run no está completado.")
    if scenario:
        _ensure_time("Scenario", [scenario.created_at, scenario.executed_at], report_cutoff)
        if scenario.status != "completed":
            raise _error("report_scenario_incomplete", "El Scenario Run no está completado.")
    if scor:
        _ensure_time("SCOR", [scor.created_at, scor.calculated_at, scor.cutoff], report_cutoff)
        if scor.status != "calculated":
            raise _error("report_scor_incomplete", "El diagnóstico SCOR no está calculado.")
    if portfolio:
        _ensure_time(
            "Portafolio",
            [portfolio.created_at, portfolio.available_at, portfolio.cutoff],
            report_cutoff,
        )
    if decision:
        _ensure_time("Decision", [decision.created_at, decision.decision_cutoff], report_cutoff)
        if decision.status != "completed":
            raise _error("report_decision_incomplete", "El Decision Run no está completado.")
    if explanation:
        _ensure_time(
            "Explanation",
            [explanation.created_at, explanation.available_at, explanation.cutoff],
            report_cutoff,
        )
        if explanation.status != "completed":
            raise _error("report_explanation_incomplete", "La explicación no está completada.")

    if forecast and scenario and scenario.forecast_run_id != forecast.id:
        raise _error("report_source_incompatible", "El escenario pertenece a otro Forecast Run.")
    if forecast and decision and decision.forecast_run_id != forecast.id:
        raise _error(
            "report_source_incompatible", "El análisis de decisión pertenece a otro Forecast Run."
        )
    if forecast and explanation and explanation.forecast_run_id != forecast.id:
        raise _error("report_source_incompatible", "La explicación pertenece a otro Forecast Run.")
    if forecast and portfolio and forecast.id not in portfolio.forecast_run_ids:
        raise _error("report_source_incompatible", "El Portafolio no contiene el Forecast Run.")
    if forecast and scor:
        if scor.forecast_run_id and scor.forecast_run_id != forecast.id:
            raise _error("report_source_incompatible", "SCOR referencia otro Forecast Run.")
        if scor.source_dataset_id and scor.source_dataset_id != forecast.dataset_id:
            raise _error("report_source_incompatible", "SCOR pertenece a otro dataset.")
    if decision and scenario and decision.scenario_run_id != scenario.id:
        raise _error("report_source_incompatible", "El escenario no coincide con Decision Run.")
    if decision and scor:
        frozen = decision.source_snapshot.get("scor")
        frozen_id = frozen.get("scor_assessment_id") if isinstance(frozen, dict) else None
        if frozen_id != scor.id:
            raise _error("report_source_incompatible", "SCOR no coincide con Decision Run.")
    if decision and portfolio:
        frozen = decision.source_snapshot.get("portfolio")
        frozen_id = frozen.get("portfolio_run_id") if isinstance(frozen, dict) else None
        if frozen_id != portfolio.id:
            raise _error("report_source_incompatible", "Portafolio no coincide con Decision Run.")
    if explanation:
        checks = {
            "scenario": scenario.id if scenario else None,
            "scor": scor.id if scor else None,
            "portfolio": portfolio.id if portfolio else None,
            "decision": decision.id if decision else None,
        }
        for key, requested in checks.items():
            if requested and _layer_id(explanation.source_snapshot, key) != requested:
                raise _error(
                    "report_source_incompatible",
                    f"La capa {key} no coincide con la explicación congelada.",
                )

    datasets = {
        value
        for value in [
            forecast.dataset_id if forecast else None,
            scenario.dataset_id if scenario else None,
            scor.source_dataset_id if scor else None,
            portfolio.dataset_id if portfolio else None,
            decision.dataset_id if decision else None,
            explanation.dataset_id if explanation else None,
        ]
        if value
    }
    if len(datasets) > 1:
        raise _error("report_source_incompatible", "Las fuentes pertenecen a datasets distintos.")
    return {
        "forecast": forecast,
        "scenario": scenario,
        "scor": scor,
        "portfolio": portfolio,
        "decision": decision,
        "explanation": explanation,
        "dataset_id": next(iter(datasets), None),
    }
