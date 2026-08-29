# NEXORA — Demand Intelligence System

NEXORA is a professional demand-intelligence workspace. Milestone 2 adds Data Studio: a guided workflow for importing company CSV/Excel files, confirming detected columns, auditing data quality, and preparing a traceable dataset contract. It intentionally contains **no forecasting, machine learning, external integrations, or inventory optimization**.

## What is included

- **Web application:** Next.js, strict TypeScript, Tailwind CSS, responsive navigation.
- **API:** Python, FastAPI, typed schemas, modular routes and services.
- **Data Studio:** CSV, XLSX, and XLS import; demo data; mapping; quality audit; readiness score.
- **Data foundation:** SQLAlchemy metadata in SQLite plus safe local source/canonical files under `data/`.
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
Leave this window running. Data Studio also needs the backend below.

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

### Try Data Studio

With both PowerShell windows still running:

1. Open [http://localhost:3000/data-studio](http://localhost:3000/data-studio).
2. Choose **Use demo dataset** for a complete built-in example, or drop/select a `.csv`, `.xlsx`, or `.xls` file.
3. For a workbook with multiple sheets, choose the sheet to inspect.
4. In **Map**, confirm which source columns represent Date, Demand, Product, and optional context. Date and Demand are required; Product can remain empty for a single time series.
5. Select **Save & validate**. Review errors, warnings, frequency, outliers, gaps, possible stockouts, and the Data Readiness breakdown.
6. If there are no critical errors, select **Mark dataset ready**. This records readiness but does not run a forecast.

Data Readiness is a deterministic weighted score covering structure, temporal continuity, demand quality, historical coverage, product coverage, and optional context. The validation view shows exactly where points were lost.

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
data/            Ignored SQLite, uploads, processed files, and generated demo data
docs/            Architecture decisions and boundaries
tests/           Future cross-application tests
```

See [docs/data-studio.md](docs/data-studio.md) for roles, heuristics, score weights, demo anomalies, storage, and current limitations. The broader boundaries remain in [docs/architecture.md](docs/architecture.md).
