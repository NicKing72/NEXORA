# Repository Guidelines

## Project Structure & Module Organization

NEXORA is a pnpm monorepo with two independent applications. `apps/web/` contains the Next.js App Router frontend; Data Studio components live under `components/data-studio/` with contracts and API calls in `lib/`. `apps/api/` contains FastAPI routes, schemas, services, models, configuration, and SQLAlchemy infrastructure. Data Studio logic belongs in `services/data_studio/`, not route handlers. Backend tests live in `apps/api/tests/`; architecture notes are in `docs/`. SQLite, uploads, canonical files, and generated demo instances live under ignored `data/` paths.

## Build, Test, and Development Commands

- `pnpm install` — install frontend dependencies from the repository root.
- `pnpm dev` — run Next.js at `http://localhost:3000`.
- `pnpm build` — create the production frontend build.
- `pnpm lint` / `pnpm typecheck` — run ESLint and strict TypeScript checks.
- `python -m pip install -e ".\apps\api[dev]"` — install API and test tools.
- `uvicorn --app-dir apps/api/src nexora_api.main:app --reload` — run the API.
- `python -m pytest apps/api/tests` — run backend tests.
- `python -m ruff check apps/api` — lint Python code.

## Coding Style & Naming Conventions

Use strict TypeScript, functional React components, two-space indentation, `PascalCase` components, and `camelCase` variables. Use Tailwind for utilities and shared tokens from `app/globals.css` for the visual system. Python targets 3.11+, uses four-space indentation and type annotations, and is checked by Ruff. Use `snake_case` for Python modules/functions and `PascalCase` for classes. Keep endpoint handlers thin; place contracts in `schemas/` and workflows in `services/`.

## Testing Guidelines

Add deterministic tests for every endpoint or behavior change. Name Python tests `test_<outcome>` in `test_<feature>.py`. Use isolated temporary storage and an in-memory SQLite database. Data Studio changes must cover upload, mapping, quality, readiness, and demo behavior. Frontend lint, typecheck, and production build must remain successful.

## Commit & Pull Request Guidelines

Use imperative Conventional Commits, such as `feat(web): add command center shell` or `test(api): cover health endpoint`. Keep PRs focused, describe verification, link issues, and include screenshots for UI changes. Explicitly identify schema, dependency, environment, or migration changes.

## Security & Scope

Never commit `.env`, credentials, local databases, uploads, canonical datasets, or generated output. Update `.env.example` for new settings. Treat filenames as untrusted and keep paths beneath the configured data root. Do not add forecasting, machine learning, inventory optimization, or external integrations until a later milestone authorizes them.
