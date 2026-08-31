"""Select compatible Forecast Runs and freeze their persisted points."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import ForecastRun


def series_key(run: ForecastRun) -> str:
    return "|".join(
        [
            run.dataset_id,
            run.product or "__all_products__",
            run.location or "__all_locations__",
            run.category or "__all_categories__",
            run.frequency,
        ]
    )


def _query(db: Session):
    return db.query(ForecastRun).options(
        selectinload(ForecastRun.points),
        selectinload(ForecastRun.model_results),
        selectinload(ForecastRun.dataset),
    )


def select_forecast_runs(
    db: Session,
    *,
    dataset_id: str | None,
    forecast_run_ids: list[str],
    cutoff: datetime,
    filters: dict[str, str | None],
) -> list[ForecastRun]:
    query = _query(db).filter(
        ForecastRun.status == "completed",
        ForecastRun.created_at <= cutoff,
    )
    if forecast_run_ids:
        query = query.filter(ForecastRun.id.in_(forecast_run_ids))
    elif dataset_id:
        query = query.filter(ForecastRun.dataset_id == dataset_id)
    for field in ("product", "location", "category"):
        value = filters.get(field)
        if value:
            query = query.filter(getattr(ForecastRun, field) == value)
    candidates = query.all()
    if forecast_run_ids:
        found_ids = {run.id for run in candidates}
        unavailable = sorted(set(forecast_run_ids) - found_ids)
        if unavailable:
            raise DataStudioError(
                "portfolio_forecast_unavailable",
                "Uno o más Forecast Runs no existían o no estaban disponibles en el cutoff.",
                409,
            )
    if not candidates:
        raise DataStudioError(
            "portfolio_no_forecasts",
            "No existen Forecast Runs oficiales compatibles disponibles para el cutoff.",
            409,
        )
    dataset_ids = {run.dataset_id for run in candidates}
    if len(dataset_ids) != 1:
        raise DataStudioError(
            "portfolio_dataset_mismatch",
            "Un Portfolio Run no puede mezclar datasets distintos.",
            409,
        )

    selected: dict[str, ForecastRun] = {}
    for run in candidates:
        key = series_key(run)
        current = selected.get(key)
        if current is None or (run.created_at, run.id) > (current.created_at, current.id):
            selected[key] = run
    output = sorted(selected.values(), key=lambda run: series_key(run))
    frequencies = {run.frequency for run in output}
    horizons = {run.requested_horizon for run in output}
    if len(frequencies) != 1 or len(horizons) != 1:
        raise DataStudioError(
            "portfolio_incompatible_forecasts",
            "La comparación requiere una frecuencia y un horizonte comunes; "
            "no se agregan unidades incompatibles.",
            409,
        )
    for run in output:
        if not run.points or not run.champion_model:
            raise DataStudioError(
                "portfolio_incomplete_forecast",
                "Todos los Forecast Runs deben conservar Champion y puntos persistidos.",
                409,
            )
    return output


def freeze_forecast(run: ForecastRun) -> dict[str, object]:
    points = [
        {
            "timestamp": point.timestamp.date().isoformat(),
            "forecast": float(point.forecast),
            "lower_80": point.lower_80,
            "upper_80": point.upper_80,
            "lower_95": point.lower_95,
            "upper_95": point.upper_95,
        }
        for point in sorted(run.points, key=lambda item: item.timestamp)
    ]
    encoded = json.dumps(points, sort_keys=True, separators=(",", ":")).encode()
    return {
        "forecast_run_id": run.id,
        "forecast_created_at": run.created_at.isoformat(),
        "data_cutoff": run.data_cutoff.isoformat(),
        "champion": run.champion_model,
        "frequency": run.frequency,
        "horizon": run.requested_horizon,
        "points": points,
        "points_sha256": hashlib.sha256(encoded).hexdigest(),
    }
