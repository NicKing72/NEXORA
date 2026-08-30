"""Temporal availability rules that prevent future-information leakage."""

from datetime import datetime

from sqlalchemy.orm import Query

from nexora_api.models.context import ContextSignal


class ContextAvailabilityService:
    """Apply knowledge-time cutoffs independently from event-time filters."""

    @staticmethod
    def was_available(signal: ContextSignal, cutoff: datetime) -> bool:
        return signal.available_at <= cutoff

    @staticmethod
    def apply_cutoff(query: Query[ContextSignal], cutoff: datetime) -> Query[ContextSignal]:
        return query.filter(ContextSignal.available_at <= cutoff)

