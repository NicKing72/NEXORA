"""Application service for Context Engine persistence and queries."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.context import ContextSignal, ContextSignalAudit
from nexora_api.models.dataset import Dataset
from nexora_api.schemas.context import ContextSignalCreate, ContextSignalInput, ContextSignalUpdate
from nexora_api.services.context.availability import ContextAvailabilityService
from nexora_api.services.context.demo import DEMO_SOURCE_NAME, build_demo_signals
from nexora_api.services.context.relevance import SeriesContext, match_signal

STATUS_TRANSITIONS = {
    "detected": {"reviewed", "confirmed", "dismissed", "expired"},
    "reviewed": {"confirmed", "dismissed", "expired"},
    "confirmed": {"reviewed", "dismissed", "expired"},
    "dismissed": {"reviewed", "confirmed", "expired"},
    "expired": set(),
}


def _now() -> datetime:
    return datetime.now(UTC)


def serialize_signal(signal: ContextSignal) -> dict[str, object]:
    return {
        "id": signal.id,
        "dataset_id": signal.dataset_id,
        "signal_family": signal.signal_family,
        "signal_type": signal.signal_type,
        "title": signal.title,
        "description": signal.description,
        "event_start": signal.event_start,
        "event_end": signal.event_end,
        "observed_at": signal.observed_at,
        "available_at": signal.available_at,
        "status": signal.status,
        "source_type": signal.source_type,
        "source_name": signal.source_name,
        "source_reference": signal.source_reference,
        "confidence": signal.confidence,
        "intensity": signal.intensity,
        "knowledge_type": signal.knowledge_type,
        "scope_type": signal.scope_type,
        "country": signal.country,
        "region": signal.region,
        "product": signal.product,
        "category": signal.category,
        "location": signal.location,
        "channel": signal.channel,
        "market": signal.market,
        "metadata": signal.metadata_json,
        "impact_status": signal.impact_status,
        "created_at": signal.created_at,
        "updated_at": signal.updated_at,
    }


def _require_dataset(db: Session, dataset_id: str) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).one_or_none()
    if dataset is None:
        raise DataStudioError("dataset_not_found", "The requested dataset does not exist.", 404)
    return dataset


def require_signal(db: Session, signal_id: str) -> ContextSignal:
    signal = db.query(ContextSignal).filter(ContextSignal.id == signal_id).one_or_none()
    if signal is None:
        raise DataStudioError("context_signal_not_found", "The context signal does not exist.", 404)
    return signal


def _audit(
    db: Session, signal: ContextSignal, action: str, changes: dict[str, object]
) -> None:
    def json_safe(value: object) -> object:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [json_safe(item) for item in value]
        return value

    db.add(ContextSignalAudit(signal=signal, action=action, changes=json_safe(changes)))


def create_manual_signal(db: Session, payload: ContextSignalCreate) -> ContextSignal:
    if payload.dataset_id:
        _require_dataset(db, payload.dataset_id)
    values = payload.dict()
    metadata = values.pop("metadata")
    signal = ContextSignal(
        id=str(uuid4()),
        **values,
        metadata_json=metadata,
        status="confirmed",
        source_type="manual",
        source_name="usuario/manual",
        impact_status="not_estimated",
    )
    db.add(signal)
    _audit(db, signal, "created", {"source_type": "manual", "status": "confirmed"})
    db.commit()
    db.refresh(signal)
    return signal


def update_signal(
    db: Session, signal_id: str, payload: ContextSignalUpdate
) -> ContextSignal:
    signal = require_signal(db, signal_id)
    updates = payload.dict(exclude_unset=True)
    if not updates:
        return signal

    current = {
        field: getattr(signal, "metadata_json" if field == "metadata" else field)
        for field in ContextSignalInput.__fields__
    }
    current.update(updates)
    try:
        validated = ContextSignalInput(**current)
    except ValidationError as error:
        raise DataStudioError(
            "invalid_context_signal", "The updated signal is not temporally valid.", 422
        ) from error
    normalized = validated.dict()

    changes: dict[str, object] = {}
    for field in updates:
        attribute = "metadata_json" if field == "metadata" else field
        old_value = getattr(signal, attribute)
        new_value = normalized[field]
        if old_value != new_value:
            changes[field] = {"from": old_value, "to": new_value}
            setattr(signal, attribute, new_value)

    if changes:
        signal.updated_at = _now()
        _audit(db, signal, "updated", changes)
        db.commit()
        db.refresh(signal)
    return signal


def change_signal_status(db: Session, signal_id: str, status: str) -> ContextSignal:
    signal = require_signal(db, signal_id)
    if status == signal.status:
        return signal
    if status not in STATUS_TRANSITIONS.get(signal.status, set()):
        raise DataStudioError(
            "invalid_status_transition",
            f"Status cannot change from {signal.status} to {status}.",
            409,
        )
    previous = signal.status
    signal.status = status
    signal.updated_at = _now()
    _audit(db, signal, "status_changed", {"status": {"from": previous, "to": status}})
    db.commit()
    db.refresh(signal)
    return signal


def _base_query(
    db: Session,
    *,
    dataset_id: str | None = None,
    signal_family: str | None = None,
    status: str | None = None,
    source_type: str | None = None,
    product: str | None = None,
    category: str | None = None,
    location: str | None = None,
    event_from: datetime | None = None,
    event_to: datetime | None = None,
    cutoff: datetime | None = None,
) -> Query[ContextSignal]:
    query = db.query(ContextSignal)
    if dataset_id:
        query = query.filter(ContextSignal.dataset_id == dataset_id)
    if signal_family:
        query = query.filter(ContextSignal.signal_family == signal_family)
    if status:
        query = query.filter(ContextSignal.status == status)
    if source_type:
        query = query.filter(ContextSignal.source_type == source_type)
    if product:
        query = query.filter(or_(ContextSignal.product.is_(None), ContextSignal.product == product))
    if category:
        query = query.filter(
            or_(ContextSignal.category.is_(None), ContextSignal.category == category)
        )
    if location:
        query = query.filter(
            or_(ContextSignal.location.is_(None), ContextSignal.location == location)
        )
    if event_from:
        query = query.filter(
            or_(ContextSignal.event_end.is_(None), ContextSignal.event_end >= event_from)
        )
    if event_to:
        query = query.filter(ContextSignal.event_start <= event_to)
    if cutoff:
        query = ContextAvailabilityService.apply_cutoff(query, cutoff)
    return query


def list_signals(db: Session, **filters: object) -> list[ContextSignal]:
    return _base_query(db, **filters).order_by(ContextSignal.event_start, ContextSignal.id).all()


def relevant_signals(
    db: Session,
    *,
    dataset_id: str | None,
    context: SeriesContext,
    cutoff: datetime | None = None,
    event_from: datetime | None = None,
    event_to: datetime | None = None,
) -> list[dict[str, object]]:
    signals = list_signals(
        db,
        dataset_id=dataset_id,
        cutoff=cutoff,
        event_from=event_from,
        event_to=event_to,
    )
    matches: list[dict[str, object]] = []
    for signal in signals:
        applies, reasons = match_signal(signal, context)
        if applies:
            matches.append({"signal": serialize_signal(signal), "match_reasons": reasons})
    return matches


def regenerate_demo_context(db: Session, dataset_id: str) -> list[ContextSignal]:
    dataset = _require_dataset(db, dataset_id)
    if dataset.source_type != "demo":
        raise DataStudioError(
            "demo_context_requires_demo_dataset",
            "Demo context can only be generated for the synthetic demo dataset.",
            409,
        )
    existing = (
        db.query(ContextSignal)
        .filter(
            ContextSignal.dataset_id == dataset_id,
            ContextSignal.source_name == DEMO_SOURCE_NAME,
        )
        .all()
    )
    for signal in existing:
        db.delete(signal)
    db.flush()
    signals = build_demo_signals(dataset_id)
    for signal in signals:
        db.add(signal)
        _audit(db, signal, "demo_generated", {"demo_key": signal.metadata_json["demo_key"]})
    db.commit()
    for signal in signals:
        db.refresh(signal)
    return signals
