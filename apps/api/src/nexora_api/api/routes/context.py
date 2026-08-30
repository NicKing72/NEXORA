"""Versioned REST endpoints for Context Engine signals."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from nexora_api.db.session import get_database_session
from nexora_api.schemas.context import (
    ContextSignalCreate,
    ContextSignalResponse,
    ContextSignalStatusUpdate,
    ContextSignalUpdate,
    DemoContextRequest,
    DemoContextResponse,
    RelevantSignalResponse,
    SignalFamily,
    SignalStatus,
    SourceType,
)
from nexora_api.services.context.relevance import SeriesContext
from nexora_api.services.context.service import (
    change_signal_status,
    create_manual_signal,
    list_signals,
    regenerate_demo_context,
    relevant_signals,
    require_signal,
    serialize_signal,
    update_signal,
)

router = APIRouter(prefix="/api/v1/context-signals", tags=["context-engine"])


@router.get("", response_model=list[ContextSignalResponse])
def retrieve_signals(
    dataset_id: UUID | None = None,
    signal_family: SignalFamily | None = None,
    status_filter: SignalStatus | None = Query(None, alias="status"),
    source_type: SourceType | None = None,
    product: str | None = Query(None, max_length=255),
    category: str | None = Query(None, max_length=255),
    location: str | None = Query(None, max_length=255),
    event_from: datetime | None = None,
    event_to: datetime | None = None,
    cutoff: datetime | None = None,
    db: Session = Depends(get_database_session),
) -> list[dict[str, object]]:
    signals = list_signals(
        db,
        dataset_id=str(dataset_id) if dataset_id else None,
        signal_family=signal_family,
        status=status_filter,
        source_type=source_type,
        product=product,
        category=category,
        location=location,
        event_from=event_from,
        event_to=event_to,
        cutoff=cutoff,
    )
    return [serialize_signal(signal) for signal in signals]


@router.post("", response_model=ContextSignalResponse, status_code=status.HTTP_201_CREATED)
def create_signal(
    payload: ContextSignalCreate,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    return serialize_signal(create_manual_signal(db, payload))


@router.get("/available", response_model=list[ContextSignalResponse])
def retrieve_available_signals(
    cutoff: datetime,
    dataset_id: UUID | None = None,
    db: Session = Depends(get_database_session),
) -> list[dict[str, object]]:
    signals = list_signals(
        db,
        dataset_id=str(dataset_id) if dataset_id else None,
        cutoff=cutoff,
    )
    return [serialize_signal(signal) for signal in signals]


@router.get("/relevant", response_model=list[RelevantSignalResponse])
def retrieve_relevant_signals(
    dataset_id: UUID | None = None,
    product: str | None = Query(None, max_length=255),
    category: str | None = Query(None, max_length=255),
    location: str | None = Query(None, max_length=255),
    channel: str | None = Query(None, max_length=255),
    market: str | None = Query(None, max_length=255),
    country: str | None = Query(None, max_length=120),
    region: str | None = Query(None, max_length=120),
    cutoff: datetime | None = None,
    event_from: datetime | None = None,
    event_to: datetime | None = None,
    db: Session = Depends(get_database_session),
) -> list[dict[str, object]]:
    return relevant_signals(
        db,
        dataset_id=str(dataset_id) if dataset_id else None,
        context=SeriesContext(
            product=product,
            category=category,
            location=location,
            channel=channel,
            market=market,
            country=country,
            region=region,
        ),
        cutoff=cutoff,
        event_from=event_from,
        event_to=event_to,
    )


@router.post("/demo/regenerate", response_model=DemoContextResponse)
def regenerate_demo(
    payload: DemoContextRequest,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    signals = regenerate_demo_context(db, payload.dataset_id)
    return {
        "dataset_id": payload.dataset_id,
        "generated": len(signals),
        "signals": [serialize_signal(signal) for signal in signals],
    }


@router.get("/{signal_id}", response_model=ContextSignalResponse)
def retrieve_signal(
    signal_id: UUID,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    return serialize_signal(require_signal(db, str(signal_id)))


@router.patch("/{signal_id}", response_model=ContextSignalResponse)
def modify_signal(
    signal_id: UUID,
    payload: ContextSignalUpdate,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    return serialize_signal(update_signal(db, str(signal_id), payload))


@router.patch("/{signal_id}/status", response_model=ContextSignalResponse)
def modify_signal_status(
    signal_id: UUID,
    payload: ContextSignalStatusUpdate,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    return serialize_signal(change_signal_status(db, str(signal_id), payload.status))
