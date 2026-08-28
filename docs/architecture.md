# NEXORA Foundation Architecture

NEXORA starts as a small monorepo with independently runnable applications:

```text
Browser → apps/web (Next.js) → apps/api (FastAPI) → data/nexora.db (SQLite)
```

## Frontend

`apps/web` uses the Next.js App Router, strict TypeScript, Tailwind CSS, and a shared application shell. Routes are statically generated from one navigation registry. The Command Center contains presentation-only foundation data; it does not calculate forecasts.

## Backend

`apps/api` separates routes, schemas, services, models, configuration, and database infrastructure. SQLAlchemy owns persistence behind a configurable database URL, allowing SQLite to be replaced by PostgreSQL later without changing endpoint contracts. No domain tables or business rules are included in Milestone 1.

## Boundaries for future milestones

- Add demand and product entities under `models/` only after their contracts are defined.
- Keep HTTP concerns in `api/routes/` and business workflows in `services/`.
- Use migrations before introducing production data.
- Do not place forecasting algorithms inside route handlers or UI components.

## Managed Windows compatibility

The foundation constrains FastAPI and Pydantic to a compatible range that can run Pydantic in pure-Python mode when Windows Application Control blocks downloaded native modules. Reassess this constraint before a framework upgrade or production deployment; it does not affect the REST or persistence boundaries.
