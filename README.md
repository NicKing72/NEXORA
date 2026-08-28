# NEXORA — Demand Intelligence System

NEXORA is the foundation of a professional demand-intelligence workspace. Milestone 1 provides a responsive Command Center, consistent placeholder modules, and a small API that confirms the system is healthy. It intentionally contains **no forecasting, machine learning, external integrations, or inventory logic**.

## What is included

- **Web application:** Next.js, strict TypeScript, Tailwind CSS, responsive navigation.
- **API:** Python, FastAPI, typed schemas, modular routes and services.
- **Data foundation:** SQLAlchemy with local SQLite storage in `data/`, configurable for a later PostgreSQL migration.
- **Quality checks:** ESLint, TypeScript compilation, Ruff, Pytest, and a production web build.

## Before you start

Install these free tools once:

1. [Node.js](https://nodejs.org/) version 20.9 or newer.
2. [Python](https://www.python.org/downloads/) version 3.11 or newer. On Windows, enable **Add Python to PATH** during installation.
3. Open PowerShell in this `NEXORA` folder.

Enable the included pnpm package manager:

```powershell
corepack enable
corepack prepare pnpm@11.19.0 --activate
```

## Start the frontend

In the first PowerShell window, run:

```powershell
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). Use the left navigation to move between Command Center and the nine foundation modules.

## Start the backend

Open a **second** PowerShell window in the same folder, then run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".\apps\api[dev]"
Copy-Item .env.example .env
uvicorn --app-dir apps/api/src nexora_api.main:app --reload --port 8000
```

Confirm the API is working by opening [http://localhost:8000/health](http://localhost:8000/health). You should see JSON containing `"status": "ok"`. Interactive API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

To stop either application, return to its PowerShell window and press **Ctrl+C**.

> If PowerShell blocks environment activation, run `.\.venv\Scripts\python.exe` in place of `python` and `.\.venv\Scripts\uvicorn.exe` in place of `uvicorn`.

> On managed Windows computers, **Application Control** may block Pydantic's downloaded native module. If that exact message appears, run `$env:SKIP_CYTHON = "1"`, then `python -m pip install --force-reinstall --no-binary pydantic "pydantic>=1.10.21,<2.0"`, and repeat the API install command. This keeps the workaround inside `.venv`.

## Run quality checks

With frontend dependencies installed:

```powershell
pnpm lint
pnpm typecheck
pnpm build
```

With the Python virtual environment active:

```powershell
python -m ruff check apps/api
python -m pytest apps/api/tests
```

## Repository map

```text
apps/web/        Next.js interface and navigation
apps/api/        FastAPI application and API tests
data/            Local SQLite database location
docs/            Architecture decisions and boundaries
tests/           Future cross-application tests
```

See [docs/architecture.md](docs/architecture.md) for the technical boundaries prepared for future milestones.
