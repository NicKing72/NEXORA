"""Versioned synchronous Forecast Core endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from nexora_api.api.routes.data_studio import get_storage_service
from nexora_api.db.session import get_database_session
from nexora_api.schemas.forecast import (
    ForecastFoldResponse,
    ForecastModelResponse,
    ForecastPointResponse,
    ForecastPreflightResponse,
    ForecastRunRequest,
    ForecastRunResponse,
    ForecastRunSummary,
)
from nexora_api.services.data_studio.storage import StorageService
from nexora_api.services.forecasting.service import (
    build_preflight,
    execute_forecast_run,
    list_runs,
    require_run,
    serialize_fold,
    serialize_model,
    serialize_point,
    serialize_run,
)

router = APIRouter(prefix="/api/v1/forecast-runs", tags=["forecast-core"])


@router.post("/preflight", response_model=ForecastPreflightResponse)
def forecast_preflight(
    payload: ForecastRunRequest,
    db: Session = Depends(get_database_session),
    storage: StorageService = Depends(get_storage_service),
) -> dict[str, object]:
    return build_preflight(db, storage, **payload.dict())


@router.post("", response_model=ForecastRunResponse, status_code=status.HTTP_201_CREATED)
def create_forecast_run(
    payload: ForecastRunRequest,
    db: Session = Depends(get_database_session),
    storage: StorageService = Depends(get_storage_service),
) -> dict[str, object]:
    run = execute_forecast_run(db, storage, **payload.dict())
    return serialize_run(db, require_run(db, run.id), storage)


@router.get("", response_model=list[ForecastRunSummary])
def retrieve_forecast_runs(
    db: Session = Depends(get_database_session),
) -> list[dict[str, object]]:
    return list_runs(db)


@router.get("/{run_id}", response_model=ForecastRunResponse)
def retrieve_forecast_run(
    run_id: str,
    db: Session = Depends(get_database_session),
    storage: StorageService = Depends(get_storage_service),
) -> dict[str, object]:
    return serialize_run(db, require_run(db, run_id), storage)


@router.get("/{run_id}/leaderboard", response_model=list[ForecastModelResponse])
def retrieve_leaderboard(
    run_id: str,
    db: Session = Depends(get_database_session),
) -> list[dict[str, object]]:
    run = require_run(db, run_id)
    models = sorted(run.model_results, key=lambda item: (item.rank is None, item.rank or 999))
    return [serialize_model(model, include_folds=False) for model in models]


@router.get("/{run_id}/points", response_model=list[ForecastPointResponse])
def retrieve_forecast_points(
    run_id: str,
    db: Session = Depends(get_database_session),
) -> list[dict[str, object]]:
    run = require_run(db, run_id)
    return [serialize_point(point) for point in sorted(run.points, key=lambda item: item.timestamp)]


@router.get("/{run_id}/models/{model_id}", response_model=ForecastModelResponse)
def retrieve_model_detail(
    run_id: str,
    model_id: int,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    run = require_run(db, run_id)
    model = next((item for item in run.model_results if item.id == model_id), None)
    if model is None:
        from nexora_api.core.exceptions import DataStudioError

        raise DataStudioError("forecast_model_not_found", "The model result does not exist.", 404)
    return serialize_model(model)


@router.get("/{run_id}/models/{model_id}/folds", response_model=list[ForecastFoldResponse])
def retrieve_model_folds(
    run_id: str,
    model_id: int,
    db: Session = Depends(get_database_session),
) -> list[dict[str, object]]:
    run = require_run(db, run_id)
    model = next((item for item in run.model_results if item.id == model_id), None)
    if model is None:
        from nexora_api.core.exceptions import DataStudioError

        raise DataStudioError("forecast_model_not_found", "The model result does not exist.", 404)
    return [serialize_fold(fold) for fold in sorted(model.folds, key=lambda item: item.fold_index)]
