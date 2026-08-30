"""Versioned REST endpoints for contextual impact evidence."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from nexora_api.api.routes.data_studio import get_storage_service
from nexora_api.db.session import get_database_session
from nexora_api.schemas.context_impact import (
    ContextAnalogyResponse,
    ContextImpactDatasetResponse,
    ContextImpactEstimateRequest,
    ContextImpactEstimateResponse,
)
from nexora_api.services.context.impact.service import (
    estimate_signal_impact,
    get_signal_analogies,
    latest_signal_estimate,
    list_dataset_estimates,
    serialize_estimate,
)
from nexora_api.services.context.service import list_signals
from nexora_api.services.data_studio.storage import StorageService

router = APIRouter(prefix="/api/v1/context-impact", tags=["context-impact"])


@router.get(
    "/signals/{signal_id}", response_model=ContextImpactEstimateResponse | None
)
def retrieve_signal_impact(
    signal_id: UUID,
    db: Session = Depends(get_database_session),
) -> dict[str, object] | None:
    estimate = latest_signal_estimate(db, str(signal_id))
    return serialize_estimate(estimate) if estimate else None


@router.post(
    "/signals/{signal_id}/estimate", response_model=ContextImpactEstimateResponse
)
def estimate_signal(
    signal_id: UUID,
    payload: ContextImpactEstimateRequest,
    db: Session = Depends(get_database_session),
    storage: StorageService = Depends(get_storage_service),
) -> dict[str, object]:
    return serialize_estimate(
        estimate_signal_impact(db, str(signal_id), payload, storage)
    )


@router.get(
    "/signals/{signal_id}/analogies", response_model=ContextAnalogyResponse
)
def retrieve_signal_analogies(
    signal_id: UUID,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    return get_signal_analogies(db, str(signal_id))


@router.get(
    "/datasets/{dataset_id}", response_model=ContextImpactDatasetResponse
)
def retrieve_dataset_impacts(
    dataset_id: UUID,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    estimates = list_dataset_estimates(db, str(dataset_id))
    return {
        "dataset_id": str(dataset_id),
        "estimates": [serialize_estimate(estimate) for estimate in estimates],
    }


@router.post(
    "/datasets/{dataset_id}/estimate", response_model=ContextImpactDatasetResponse
)
def estimate_dataset_signals(
    dataset_id: UUID,
    payload: ContextImpactEstimateRequest,
    db: Session = Depends(get_database_session),
    storage: StorageService = Depends(get_storage_service),
) -> dict[str, object]:
    signals = list_signals(db, dataset_id=str(dataset_id))
    estimates = [
        estimate_signal_impact(db, signal.id, payload, storage)
        for signal in signals
        if signal.status not in {"dismissed", "expired"}
    ]
    return {
        "dataset_id": str(dataset_id),
        "estimates": [serialize_estimate(estimate) for estimate in estimates],
    }

