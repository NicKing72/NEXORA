"""Versioned endpoints for READY dataset series exploration."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from nexora_api.api.routes.data_studio import get_storage_service
from nexora_api.db.session import get_database_session
from nexora_api.schemas.series import (
    ReadyDatasetSummary,
    SeriesDimensionsResponse,
    SeriesProfileResponse,
    SeriesRequestFrequency,
)
from nexora_api.services.data_studio.storage import StorageService
from nexora_api.services.series.engine import (
    build_series_profile,
    get_series_dimensions,
    list_ready_datasets,
)

router = APIRouter(prefix="/api/v1/series", tags=["series-engine"])


@router.get("/datasets", response_model=list[ReadyDatasetSummary])
def retrieve_ready_datasets(
    db: Session = Depends(get_database_session),
) -> list[dict[str, object]]:
    return list_ready_datasets(db)


@router.get("/datasets/{dataset_id}/dimensions", response_model=SeriesDimensionsResponse)
def retrieve_series_dimensions(
    dataset_id: str,
    db: Session = Depends(get_database_session),
    storage: StorageService = Depends(get_storage_service),
) -> dict[str, object]:
    return get_series_dimensions(db, dataset_id, storage)


@router.get("/datasets/{dataset_id}/profile", response_model=SeriesProfileResponse)
def retrieve_series_profile(
    dataset_id: str,
    product: str | None = Query(None, max_length=255),
    location: str | None = Query(None, max_length=255),
    category: str | None = Query(None, max_length=255),
    frequency: SeriesRequestFrequency = Query("auto"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_database_session),
    storage: StorageService = Depends(get_storage_service),
) -> dict[str, object]:
    return build_series_profile(
        db,
        dataset_id,
        storage,
        product=product,
        location=location,
        category=category,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
    )
