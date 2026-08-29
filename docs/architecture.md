# NEXORA Foundation Architecture

NEXORA starts as a small monorepo with independently runnable applications:

```text
Browser → apps/web (Next.js) → apps/api (FastAPI) → SQLite metadata + canonical CSV
```

## Frontend

`apps/web` uses the Next.js App Router, strict TypeScript, Tailwind CSS, and a shared application shell. Routes are statically generated from one navigation registry. The Command Center contains presentation-only foundation data; it does not calculate forecasts.

Demand Explorer uses a modular ECharts canvas visualization. Filters are sent to the API, which returns only the selected and aggregated series instead of transferring the complete source dataset.

## Backend

`apps/api` separates routes, schemas, services, models, configuration, and database infrastructure. SQLAlchemy owns persistence behind a configurable database URL, allowing SQLite to be replaced by PostgreSQL later without changing endpoint contracts. Data Studio adds dataset metadata, mappings, quality reports, issues, and lineage records while source rows remain in filesystem-backed canonical files.

The Series Engine is a read-only service under `services/series/`. It reads the READY dataset's canonical file, applies dimension filters, performs time aggregation, associates audited quality events, and calculates descriptive profiles on demand. It does not persist explorations or modify either source file.

## Boundaries for future milestones

- Add forecasting entities only after their contracts are defined in a later milestone.
- Keep HTTP concerns in `api/routes/` and business workflows in `services/`.
- Use migrations before introducing production data.
- Do not place forecasting algorithms inside route handlers or UI components.

See [data-studio.md](data-studio.md) for ingestion and readiness and [demand-explorer.md](demand-explorer.md) for the Series Engine contract introduced in Milestone 3A.

## Managed Windows compatibility

The foundation constrains FastAPI and Pydantic to a compatible range that can run Pydantic in pure-Python mode when Windows Application Control blocks downloaded native modules. Reassess this constraint before a framework upgrade or production deployment; it does not affect the REST or persistence boundaries.
