"""Exact UUID compatibility and temporal-safety checks."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import ForecastRun
from nexora_api.models.decision import DecisionRun
from nexora_api.models.portfolio import PortfolioRun
from nexora_api.models.scenario import ScenarioRun


def resolve_sources(
    db: Session,
    *,
    forecast_run_id: str,
    scenario_run_id: str | None,
    portfolio_run_id: str | None,
    decision_run_id: str | None,
    cutoff: datetime,
) -> tuple[ForecastRun, ScenarioRun | None, PortfolioRun | None, DecisionRun | None]:
    forecast = (
        db.query(ForecastRun)
        .options(selectinload(ForecastRun.points), selectinload(ForecastRun.model_results))
        .filter(ForecastRun.id == forecast_run_id)
        .one_or_none()
    )
    if forecast is None:
        raise DataStudioError("inventory_forecast_not_found", "El Forecast Run no existe.", 404)
    if forecast.status != "completed" or forecast.created_at > cutoff:
        raise DataStudioError(
            "inventory_forecast_unavailable",
            "El Forecast Run no estaba disponible en el cutoff de inventario.",
            409,
        )
    if not forecast.points or not forecast.champion_model:
        raise DataStudioError(
            "inventory_forecast_incomplete",
            "El Forecast Run no conserva Champion y puntos persistidos.",
            409,
        )

    scenario = None
    if scenario_run_id:
        scenario = (
            db.query(ScenarioRun)
            .options(selectinload(ScenarioRun.points))
            .filter(ScenarioRun.id == scenario_run_id)
            .one_or_none()
        )
        if scenario is None:
            raise DataStudioError("inventory_scenario_not_found", "El Scenario Run no existe.", 404)
        if scenario.forecast_run_id != forecast.id or scenario.dataset_id != forecast.dataset_id:
            raise DataStudioError(
                "inventory_scenario_incompatible",
                "El Scenario Run no pertenece al Forecast Run solicitado.",
                409,
            )
        if scenario.executed_at is None or scenario.executed_at > cutoff:
            raise DataStudioError(
                "inventory_scenario_unavailable",
                "El Scenario Run no estaba ejecutado y disponible en el cutoff.",
                409,
            )

    portfolio = None
    if portfolio_run_id:
        portfolio = db.get(PortfolioRun, portfolio_run_id)
        if portfolio is None:
            raise DataStudioError(
                "inventory_portfolio_not_found", "El Portfolio Run no existe.", 404
            )
        if forecast.id not in portfolio.forecast_run_ids:
            raise DataStudioError(
                "inventory_portfolio_incompatible",
                "El Portfolio Run no contiene el Forecast Run solicitado.",
                409,
            )
        if portfolio.created_at > cutoff or portfolio.available_at > cutoff:
            raise DataStudioError(
                "inventory_portfolio_unavailable",
                "El Portfolio Run no estaba disponible en el cutoff.",
                409,
            )

    decision = None
    if decision_run_id:
        decision = db.get(DecisionRun, decision_run_id)
        if decision is None:
            raise DataStudioError("inventory_decision_not_found", "El Decision Run no existe.", 404)
        if decision.forecast_run_id != forecast.id:
            raise DataStudioError(
                "inventory_decision_incompatible",
                "El Decision Run no pertenece al Forecast Run solicitado.",
                409,
            )
        if decision.created_at > cutoff or decision.decision_cutoff > cutoff:
            raise DataStudioError(
                "inventory_decision_unavailable",
                "El Decision Run no estaba disponible en el cutoff.",
                409,
            )
    return forecast, scenario, portfolio, decision
