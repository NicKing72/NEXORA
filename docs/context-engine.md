# Context Engine Foundation

Milestone 4A introduces an auditable contextual-signal layer. Signals are descriptive evidence only: they do not enter Forecast Core, estimate demand impact, or imply causality.

## Signal contract

`ContextSignal` persists a UUID, optional READY dataset association, extensible `signal_type`, title and description, event window, observation and availability timestamps, lifecycle status, provenance, confidence, optional intensity, knowledge type, multidimensional scope, safe JSON metadata, and UTC audit timestamps. `impact_status` remains `not_estimated`.

Families are `commercial`, `competitor`, `calendar`, `weather`, `market`, `digital`, `operations`, `supply_chain`, `event`, `news`, `macro`, and `custom`. Signal types remain validated snake-case strings, so adding a new type does not require a schema migration.

Knowledge types have distinct semantics:

- `observed`: a fact learned when or after it occurred.
- `known_future`: a future event genuinely known in advance.
- `forecasted_external`: a future value produced by another forecast.
- `scenario`: a hypothetical user assumption.

Source types are `manual`, `company_data`, `api`, `web`, and `system`. Only manual creation and deterministic system demo generation are functional in 4A. Manual signals use `source_name = usuario/manual` and start as `confirmed`.

## Temporal safety

Event time and knowledge time are separate:

```text
event_start / event_end  = when the event occurs
observed_at              = when it was observed
available_at             = when NEXORA could use the information
```

`ContextAvailabilityService` applies the anti-leakage rule `available_at <= cutoff`. An event beginning May 1 but becoming available May 3 is unavailable to an analysis cut off May 2. Event dates never override that rule.

## Scope and relevance

Scopes support global, country, region, location, category, product, channel, market, and custom signals. Global signals apply to every series. For scoped signals, every explicit dimension must case-insensitively match the selected series. The relevance API returns the exact matching dimensions; no embeddings, AI, impact scoring, or causal claims are used.

## Persistence and audit

SQLite stores `context_signals` and immutable `context_signal_audit` entries for create, update, status change, and demo generation. Dismissed signals remain stored. Source references are inert text: NEXORA never opens or downloads them. Descriptions and references have length limits; metadata is limited to 16 KB.

## API

- `GET/POST /api/v1/context-signals`
- `GET/PATCH /api/v1/context-signals/{id}`
- `PATCH /api/v1/context-signals/{id}/status`
- `GET /api/v1/context-signals/available?cutoff=...`
- `GET /api/v1/context-signals/relevant?...`
- `POST /api/v1/context-signals/demo/regenerate`

List queries support dataset, family, status, source, dimension, event-window, and availability-cutoff filters. All datetimes represent instants and are persisted in UTC.

## Demo context

Nine fixed signals are generated with UUID5 identifiers derived from the demo dataset ID. They cover promotions, a holiday, a local event, stockout, supplier delay, price change, external weather outlook, and a scenario. Their source timestamps are authored in `America/Lima` and normalized to UTC for persistence. Re-running generation replaces only system demo signals; manual signals remain intact.

## Current limitations

There is no scraping, external API, LLM, estimated impact, causal inference, contextual forecasting, applied scenario simulation, or forecast modification. Forecast Core remains univariate. The audit table prepares future change-history features but 4A does not expose a full audit-history UI.
