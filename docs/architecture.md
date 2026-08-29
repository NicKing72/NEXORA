# NEXORA Foundation Architecture

NEXORA starts as a small monorepo with independently runnable applications:

```text
Browser → apps/web → apps/api → Series Engine → Forecast Core → SQLite + canonical CSV
```

## Frontend

`apps/web` uses the Next.js App Router, strict TypeScript, Tailwind CSS, and a shared application shell. Routes are statically generated from one navigation registry. The Command Center contains presentation-only foundation data; it does not calculate forecasts.

Demand Explorer uses a modular ECharts canvas visualization. Filters are sent to the API, which returns only the selected and aggregated series instead of transferring the complete source dataset.

Forecast Lab reuses the same selection contract, requests a pre-flight assessment, and executes a synchronous local Forecast Run. Its leaderboard, model detail, folds, Champion, and future chart are projections of persisted API results rather than client-side calculations.

## Backend

`apps/api` separates routes, schemas, services, models, configuration, and database infrastructure. SQLAlchemy owns persistence behind a configurable database URL, allowing SQLite to be replaced by PostgreSQL later without changing endpoint contracts. Data Studio adds dataset metadata, mappings, quality reports, issues, and lineage records while source rows remain in filesystem-backed canonical files.

The Series Engine is a read-only service under `services/series/`. It reads the READY dataset's canonical file, applies dimension filters, performs time aggregation, associates audited quality events, and calculates descriptive profiles on demand. It does not persist explorations or modify either source file.

Forecast Core lives under `services/forecasting/` and consumes Series Engine profiles. Separate modules own preparation, model adapters, expanding-window backtesting, metrics, ranking, empirical intervals, and orchestration. SQLAlchemy persists Forecast Runs, model results, folds, and future points; no fitted model pickle is stored.

## Boundaries for future milestones

- Keep future contextual/exogenous forecasting outside the univariate Forecast Core.
- Keep HTTP concerns in `api/routes/` and business workflows in `services/`.
- Use migrations before introducing production data.
- Do not place forecasting algorithms inside route handlers or UI components.

See [data-studio.md](data-studio.md), [demand-explorer.md](demand-explorer.md), and [forecast-core.md](forecast-core.md) for detailed contracts.

## Managed Windows compatibility

The project constrains FastAPI and Pydantic to a compatible range that can run Pydantic in pure-Python mode when Windows Application Control blocks downloaded native modules. Forecast adapters prefer `statsmodels`; when a managed host blocks SciPy DLL loading, they use a deterministic NumPy implementation and record `engine=numpy_deterministic_fallback` in model parameters. Reassess this compatibility path before production deployment.
