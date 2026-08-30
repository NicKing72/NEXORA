"""REST contracts for auditable contextual signals."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, root_validator, validator

SignalFamily = Literal[
    "commercial",
    "competitor",
    "calendar",
    "weather",
    "market",
    "digital",
    "operations",
    "supply_chain",
    "event",
    "news",
    "macro",
    "custom",
]
KnowledgeType = Literal["observed", "known_future", "forecasted_external", "scenario"]
SourceType = Literal["manual", "company_data", "api", "web", "system"]
SignalStatus = Literal["detected", "reviewed", "confirmed", "dismissed", "expired"]
ScopeType = Literal[
    "global",
    "country",
    "region",
    "location",
    "category",
    "product",
    "channel",
    "market",
    "custom",
]

SIGNAL_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,79}$")
SCOPE_FIELD_BY_TYPE = {
    "country": "country",
    "region": "region",
    "location": "location",
    "category": "category",
    "product": "product",
    "channel": "channel",
    "market": "market",
}


class ContextSignalInput(BaseModel):
    dataset_id: str | None = Field(None, max_length=36)
    signal_family: SignalFamily
    signal_type: str = Field(..., min_length=2, max_length=80)
    title: str = Field(..., min_length=2, max_length=160)
    description: str = Field("", max_length=2000)
    event_start: datetime
    event_end: datetime | None = None
    observed_at: datetime | None = None
    available_at: datetime
    knowledge_type: KnowledgeType
    scope_type: ScopeType = "global"
    country: str | None = Field(None, max_length=120)
    region: str | None = Field(None, max_length=120)
    product: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=255)
    location: str | None = Field(None, max_length=255)
    channel: str | None = Field(None, max_length=255)
    market: str | None = Field(None, max_length=255)
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    intensity: float | None = Field(None, ge=0.0, le=1.0)
    source_reference: str | None = Field(None, max_length=1000)
    metadata: dict[str, object] = Field(default_factory=dict)

    @validator("dataset_id")
    def validate_dataset_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            return str(UUID(value))
        except ValueError as error:
            raise ValueError("dataset_id must be a valid UUID") from error

    @validator("event_start", "event_end", "observed_at", "available_at")
    def normalize_instant(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @validator("signal_type")
    def validate_signal_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not SIGNAL_TYPE_PATTERN.fullmatch(normalized):
            raise ValueError("signal_type must use lower-case letters, numbers, and underscores")
        return normalized

    @validator(
        "title",
        "description",
        "country",
        "region",
        "product",
        "category",
        "location",
        "channel",
        "market",
        "source_reference",
        pre=True,
    )
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @validator("metadata")
    def validate_metadata_size(cls, value: dict[str, object]) -> dict[str, object]:
        if len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")) > 16_384:
            raise ValueError("metadata exceeds the 16 KB limit")
        return value

    @root_validator
    def validate_dates_and_scope(cls, values: dict[str, object]) -> dict[str, object]:
        event_start = values.get("event_start")
        event_end = values.get("event_end")
        if isinstance(event_start, datetime) and isinstance(event_end, datetime):
            if event_end < event_start:
                raise ValueError("event_end cannot be earlier than event_start")
        scope_type = values.get("scope_type")
        required_field = SCOPE_FIELD_BY_TYPE.get(str(scope_type))
        if required_field and not values.get(required_field):
            raise ValueError(f"{required_field} is required for {scope_type} scope")
        return values


class ContextSignalCreate(ContextSignalInput):
    """Manual creation contract; provenance and confirmed status are server-owned."""


class ContextSignalUpdate(BaseModel):
    signal_family: SignalFamily | None = None
    signal_type: str | None = Field(None, min_length=2, max_length=80)
    title: str | None = Field(None, min_length=2, max_length=160)
    description: str | None = Field(None, max_length=2000)
    event_start: datetime | None = None
    event_end: datetime | None = None
    observed_at: datetime | None = None
    available_at: datetime | None = None
    knowledge_type: KnowledgeType | None = None
    scope_type: ScopeType | None = None
    country: str | None = Field(None, max_length=120)
    region: str | None = Field(None, max_length=120)
    product: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=255)
    location: str | None = Field(None, max_length=255)
    channel: str | None = Field(None, max_length=255)
    market: str | None = Field(None, max_length=255)
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    intensity: float | None = Field(None, ge=0.0, le=1.0)
    source_reference: str | None = Field(None, max_length=1000)
    metadata: dict[str, object] | None = None

    @validator("event_start", "event_end", "observed_at", "available_at")
    def normalize_instant(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @validator("signal_type")
    def validate_signal_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not SIGNAL_TYPE_PATTERN.fullmatch(normalized):
            raise ValueError("signal_type must use lower-case letters, numbers, and underscores")
        return normalized

    @validator("metadata")
    def validate_metadata_size(
        cls, value: dict[str, object] | None
    ) -> dict[str, object] | None:
        if value is not None and len(
            json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")
        ) > 16_384:
            raise ValueError("metadata exceeds the 16 KB limit")
        return value


class ContextSignalStatusUpdate(BaseModel):
    status: SignalStatus


class ContextSignalResponse(BaseModel):
    id: str
    dataset_id: str | None
    signal_family: SignalFamily
    signal_type: str
    title: str
    description: str
    event_start: datetime
    event_end: datetime | None
    observed_at: datetime | None
    available_at: datetime
    status: SignalStatus
    source_type: SourceType
    source_name: str
    source_reference: str | None
    confidence: float | None
    intensity: float | None
    knowledge_type: KnowledgeType
    scope_type: ScopeType
    country: str | None
    region: str | None
    product: str | None
    category: str | None
    location: str | None
    channel: str | None
    market: str | None
    metadata: dict[str, object]
    impact_status: Literal[
        "not_estimated",
        "estimated",
        "insufficient_evidence",
        "not_observable",
        "not_applicable",
        "pending",
    ]
    created_at: datetime
    updated_at: datetime


class RelevanceReason(BaseModel):
    dimension: str
    expected: str
    actual: str


class RelevantSignalResponse(BaseModel):
    signal: ContextSignalResponse
    match_reasons: list[RelevanceReason] = Field(default_factory=list)


class DemoContextRequest(BaseModel):
    dataset_id: str = Field(..., min_length=36, max_length=36)

    @validator("dataset_id")
    def validate_dataset_id(cls, value: str) -> str:
        try:
            return str(UUID(value))
        except ValueError as error:
            raise ValueError("dataset_id must be a valid UUID") from error


class DemoContextResponse(BaseModel):
    dataset_id: str
    generated: int
    signals: list[ContextSignalResponse]
