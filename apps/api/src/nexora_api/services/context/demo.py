"""Fixed, reproducible Context Radar examples for the synthetic dataset."""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from nexora_api.models.context import ContextSignal

DEMO_SOURCE_NAME = "NEXORA demo contextual"
DEMO_SOURCE_TIMEZONE = ZoneInfo("America/Lima")


def _instant(value: str) -> datetime:
    local_value = datetime.fromisoformat(value).replace(tzinfo=DEMO_SOURCE_TIMEZONE)
    return local_value.astimezone(UTC)


DEMO_BLUEPRINTS: tuple[dict[str, object], ...] = (
    {
        "key": "own-promotion",
        "signal_family": "commercial",
        "signal_type": "own_promotion",
        "title": "Promoción de temporada NX-101",
        "description": "Campaña propia confirmada para el producto NX-101 en Lima Centro.",
        "event_start": "2025-07-14T00:00:00",
        "event_end": "2025-07-20T23:59:59",
        "observed_at": "2025-07-14T08:00:00",
        "available_at": "2025-07-10T15:00:00",
        "knowledge_type": "known_future",
        "scope_type": "product",
        "product": "NX-101",
        "location": "Lima Centro",
        "confidence": 1.0,
        "intensity": 0.7,
    },
    {
        "key": "competitor-promotion",
        "signal_family": "competitor",
        "signal_type": "competitor_promotion",
        "title": "Promoción competidora observada",
        "description": "Registro de una promoción competidora en la categoría Essentials.",
        "event_start": "2025-09-05T00:00:00",
        "event_end": "2025-09-12T23:59:59",
        "observed_at": "2025-09-06T11:30:00",
        "available_at": "2025-09-06T11:30:00",
        "knowledge_type": "observed",
        "scope_type": "category",
        "category": "Essentials",
        "location": "Lima Centro",
        "confidence": 0.72,
        "intensity": 0.5,
        "status": "reviewed",
    },
    {
        "key": "competitor-promotion-planned",
        "signal_family": "competitor",
        "signal_type": "competitor_promotion",
        "title": "Promoción competidora planificada Lima Centro",
        "description": (
            "Promoción competidora futura conocida para la categoría Essentials en "
            "Lima Centro; solo admite analogía histórica descriptiva."
        ),
        "event_start": "2026-09-05T00:00:00",
        "event_end": "2026-09-12T23:59:59",
        "observed_at": None,
        "available_at": "2026-08-20T09:00:00",
        "knowledge_type": "known_future",
        "scope_type": "category",
        "category": "Essentials",
        "location": "Lima Centro",
        "confidence": 0.78,
        "intensity": 0.5,
    },
    {
        "key": "holiday",
        "signal_family": "calendar",
        "signal_type": "holiday",
        "title": "Navidad",
        "description": (
            "Feriado conocido con anticipación y alcance global para el portafolio demo."
        ),
        "event_start": "2026-12-25T00:00:00",
        "event_end": "2026-12-25T23:59:59",
        "observed_at": None,
        "available_at": "2026-01-01T00:00:00",
        "knowledge_type": "known_future",
        "scope_type": "global",
        "confidence": 1.0,
        "intensity": 0.8,
    },
    {
        "key": "local-event",
        "signal_family": "event",
        "signal_type": "local_event",
        "title": "Feria comercial de Lima Centro",
        "description": "Evento local confirmado; su impacto sobre demanda aún no ha sido estimado.",
        "event_start": "2026-08-28T09:00:00",
        "event_end": "2026-08-30T20:00:00",
        "observed_at": None,
        "available_at": "2026-06-18T14:00:00",
        "knowledge_type": "known_future",
        "scope_type": "location",
        "location": "Lima Centro",
        "confidence": 0.95,
        "intensity": 0.6,
    },
    {
        "key": "stockout",
        "signal_family": "operations",
        "signal_type": "stockout",
        "title": "Ruptura de stock confirmada",
        "description": "Incidencia operacional registrada después de iniciarse el evento.",
        "event_start": "2025-03-03T00:00:00",
        "event_end": "2025-03-05T23:59:59",
        "observed_at": "2025-03-04T10:00:00",
        "available_at": "2025-03-04T10:15:00",
        "knowledge_type": "observed",
        "scope_type": "product",
        "product": "NX-104",
        "location": "Arequipa Norte",
        "confidence": 0.98,
        "intensity": 0.9,
    },
    {
        "key": "supplier-delay",
        "signal_family": "supply_chain",
        "signal_type": "supplier_delay",
        "title": "Retraso de proveedor",
        "description": "Aviso confirmado de retraso en el abastecimiento de la categoría Premium.",
        "event_start": "2025-11-10T00:00:00",
        "event_end": "2025-11-18T23:59:59",
        "observed_at": "2025-11-07T16:00:00",
        "available_at": "2025-11-07T16:00:00",
        "knowledge_type": "observed",
        "scope_type": "category",
        "category": "Premium",
        "confidence": 0.9,
        "intensity": 0.65,
    },
    {
        "key": "price-change",
        "signal_family": "commercial",
        "signal_type": "price_change",
        "title": "Cambio de precio programado",
        "description": "Cambio comercial conocido antes de su fecha efectiva.",
        "event_start": "2026-09-15T00:00:00",
        "event_end": None,
        "observed_at": None,
        "available_at": "2026-08-20T09:00:00",
        "knowledge_type": "known_future",
        "scope_type": "product",
        "product": "NX-101",
        "confidence": 1.0,
        "intensity": 0.4,
    },
    {
        "key": "weather-outlook",
        "signal_family": "weather",
        "signal_type": "weather_event",
        "title": "Perspectiva climática externa",
        "description": (
            "Ejemplo de forecast externo; no proviene de una API real y no modifica pronósticos."
        ),
        "event_start": "2026-10-01T00:00:00",
        "event_end": "2026-10-07T23:59:59",
        "observed_at": None,
        "available_at": "2026-08-25T12:00:00",
        "knowledge_type": "forecasted_external",
        "scope_type": "region",
        "region": "Lima",
        "confidence": 0.62,
        "intensity": 0.5,
    },
    {
        "key": "scenario-campaign",
        "signal_family": "custom",
        "signal_type": "campaign",
        "title": "Supuesto de campaña ampliada",
        "description": (
            "Escenario hipotético de demostración; no es un hecho ni participa en el forecast."
        ),
        "event_start": "2026-11-01T00:00:00",
        "event_end": "2026-11-14T23:59:59",
        "observed_at": None,
        "available_at": "2026-08-29T12:00:00",
        "knowledge_type": "scenario",
        "scope_type": "location",
        "location": "Lima Centro",
        "confidence": 0.5,
        "intensity": 0.75,
    },
)


def build_demo_signals(dataset_id: str) -> list[ContextSignal]:
    signals: list[ContextSignal] = []
    for blueprint in DEMO_BLUEPRINTS:
        values = dict(blueprint)
        key = str(values.pop("key"))
        for field in ("event_start", "event_end", "observed_at", "available_at"):
            if values[field] is not None:
                values[field] = _instant(str(values[field]))
        signals.append(
            ContextSignal(
                id=str(uuid5(NAMESPACE_URL, f"nexora:context:{dataset_id}:{key}")),
                dataset_id=dataset_id,
                source_type="system",
                source_name=DEMO_SOURCE_NAME,
                source_reference=f"demo://context/{key}",
                metadata_json={"demo_key": key, "reproducible": True},
                status=str(values.pop("status", "confirmed")),
                impact_status="not_estimated",
                **values,
            )
        )
    return signals
