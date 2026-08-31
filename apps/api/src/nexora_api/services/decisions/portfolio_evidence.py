"""Prepare immutable, temporally safe Portfolio evidence for Decision Engine."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime

from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import ForecastRun
from nexora_api.models.portfolio import PortfolioItem, PortfolioRun


def _item_snapshot(item: PortfolioItem) -> dict[str, object]:
    return {
        "id": item.id,
        "rank": item.rank,
        "series_key": item.series_key,
        "product": item.product,
        "location": item.location,
        "category": item.category,
        "family": item.family,
        "forecast_run_id": item.forecast_run_id,
        "champion": item.champion,
        "forecast_horizon": item.forecast_horizon,
        "forecast_frequency": item.forecast_frequency,
        "forecast_total": item.forecast_total,
        "forecast_average": item.forecast_average,
        "forecast_peak": item.forecast_peak,
        "forecast_minimum": item.forecast_minimum,
        "forecast_variability": item.forecast_variability,
        "interval_information": deepcopy(item.interval_json),
        "operational_inputs": deepcopy(item.operational_inputs_json),
        "current_inventory": item.current_inventory,
        "inbound_inventory": item.inbound_inventory,
        "safety_stock": item.safety_stock,
        "lead_time": item.lead_time,
        "inventory_coverage": item.inventory_coverage,
        "coverage_status": item.coverage_status,
        "projected_exposure": item.projected_exposure,
        "operational_data_completeness": item.operational_data_completeness,
        "risk_level": item.risk_level,
        "priority_score": item.priority_score,
        "score_status": item.score_status,
        "score_components": deepcopy(item.score_components),
        "priority_reasons": list(item.priority_reasons),
        "missing_inputs": list(item.missing_inputs),
        "warnings": list(item.warnings),
        "provenance": deepcopy(item.provenance_json),
    }


def _query(db: Session):
    return db.query(PortfolioRun).options(selectinload(PortfolioRun.items))


def _related_item(run: PortfolioRun, forecast: ForecastRun) -> PortfolioItem | None:
    return next((item for item in run.items if item.forecast_run_id == forecast.id), None)


def _compatible(run: PortfolioRun, forecast: ForecastRun, cutoff: datetime) -> bool:
    item = _related_item(run, forecast)
    return bool(
        run.source_mode == "official"
        and run.dataset_id == forecast.dataset_id
        and run.created_at <= cutoff
        and run.available_at <= cutoff
        and run.cutoff <= cutoff
        and forecast.id in run.forecast_run_ids
        and item is not None
        and item.forecast_frequency == forecast.frequency
        and item.forecast_horizon == forecast.requested_horizon
        and item.product == forecast.product
        and item.location == forecast.location
        and item.category == forecast.category
    )


def list_available_portfolios(
    db: Session, forecast: ForecastRun, decision_cutoff: datetime
) -> list[dict[str, object]]:
    runs = (
        _query(db)
        .filter(PortfolioRun.dataset_id == forecast.dataset_id)
        .order_by(PortfolioRun.created_at.desc(), PortfolioRun.id)
        .all()
    )
    output: list[dict[str, object]] = []
    for run in runs:
        if not _compatible(run, forecast, decision_cutoff):
            continue
        item = _related_item(run, forecast)
        assert item is not None
        output.append(
            {
                "id": run.id,
                "dataset_id": run.dataset_id,
                "source_mode": run.source_mode,
                "cutoff": run.cutoff.isoformat(),
                "created_at": run.created_at.isoformat(),
                "available_at": run.available_at.isoformat(),
                "calculation_version": run.calculation_version,
                "number_of_series": run.number_of_series,
                "critical_high_count": int(
                    run.summary_json.get("risk_counts", {}).get("critical", 0)
                )
                + int(run.summary_json.get("risk_counts", {}).get("high", 0)),
                "incomplete_count": int(
                    run.summary_json.get("completeness_counts", {}).get("partial_data", 0)
                )
                + int(
                    run.summary_json.get("completeness_counts", {}).get(
                        "insufficient_data", 0
                    )
                ),
                "coverage_evaluable_series": run.summary_json.get(
                    "coverage_evaluable_series", 0
                ),
                "forecast_run_ids": list(run.forecast_run_ids),
                "related_item": {
                    "id": item.id,
                    "rank": item.rank,
                    "product": item.product,
                    "location": item.location,
                    "risk_level": item.risk_level,
                    "priority_score": item.priority_score,
                    "score_status": item.score_status,
                },
            }
        )
    return output


def prepare_portfolio_evidence(
    db: Session,
    forecast: ForecastRun,
    portfolio_run_id: str,
    decision_cutoff: datetime,
) -> dict[str, object]:
    run = _query(db).filter(PortfolioRun.id == portfolio_run_id).one_or_none()
    if run is None:
        raise DataStudioError(
            "decision_portfolio_not_found", "El Portfolio Run seleccionado no existe.", 404
        )
    if run.source_mode != "official":
        raise DataStudioError(
            "decision_portfolio_demo_not_allowed",
            "El demo desacoplado de Portafolio no puede mezclarse con una decisión real.",
            409,
        )
    if run.created_at > decision_cutoff or run.available_at > decision_cutoff:
        raise DataStudioError(
            "decision_portfolio_after_cutoff",
            "El Portfolio Run aún no estaba disponible en la fecha de corte de decisión.",
            409,
        )
    if run.cutoff > decision_cutoff:
        raise DataStudioError(
            "decision_portfolio_future_state",
            "El corte del Portafolio contiene estado posterior al corte de decisión.",
            409,
        )
    if not _compatible(run, forecast, decision_cutoff):
        raise DataStudioError(
            "decision_portfolio_incompatible",
            "El Portfolio Run no es compatible con el Forecast Run seleccionado.",
            409,
        )
    item = _related_item(run, forecast)
    assert item is not None
    ranking = [
        _item_snapshot(entry)
        for entry in sorted(run.items, key=lambda entry: (entry.rank, entry.series_key))
    ]
    return {
        "portfolio_run_id": run.id,
        "dataset_id": run.dataset_id,
        "source_mode": run.source_mode,
        "cutoff": run.cutoff.isoformat(),
        "created_at": run.created_at.isoformat(),
        "available_at": run.available_at.isoformat(),
        "calculation_version": run.calculation_version,
        "number_of_series": run.number_of_series,
        "forecast_run_ids": list(run.forecast_run_ids),
        "related_forecast_run_id": forecast.id,
        "summary": deepcopy(run.summary_json),
        "warnings": list(run.warnings),
        "provenance": deepcopy(run.provenance_json),
        "ranking": ranking,
        "related_items": [_item_snapshot(item)],
        "decision_cutoff": decision_cutoff.isoformat(),
        "snapshot_immutable": True,
        "priority_score_is_probability": False,
        "automatic_execution": False,
    }
