# NEXORA — Demand Intelligence System

NEXORA is a professional demand-intelligence workspace. Milestone 4A adds an auditable Context Engine and Context Radar while keeping Forecast Core strictly univariate. Context signals are visible evidence only: they do not change forecasts or estimate demand impact.

## What is included

- **Web application:** Next.js, strict TypeScript, Tailwind CSS, responsive navigation.
- **API:** Python, FastAPI, typed schemas, modular routes and services.
- **Data Studio:** CSV, XLSX, and XLS import; demo data; mapping; quality audit; readiness score.
- **Demand Explorer:** product, location, category, date, and frequency filters; interactive history; quality markers; descriptive pattern analysis.
- **Forecast Lab:** explicit training preparation, seven statistical candidates, temporal backtesting, auditable Champion ranking, empirical intervals, and persisted runs.
- **Context Radar:** manual and reproducible demo signals, deterministic scope matching, provenance, lifecycle status, and anti-leakage availability cutoffs.
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

### Explore a demand series

After marking a dataset as **LISTO** in Estudio de Datos:

1. Open [http://localhost:3000/demand-explorer](http://localhost:3000/demand-explorer).
2. Choose a dataset, product, location, optional category, period, and frequency.
3. Use **Todos los productos** or **Todas las ubicaciones** to inspect an explicitly labeled aggregate series.
4. Hover over the chart and use its lower slider or mouse wheel to zoom.
5. Toggle values atípicos, faltantes, rupturas de stock, and demanda cero.
6. Review resulting-series statistics separately from source-data quality, then inspect trend, intermittence, seasonality evidence, and preliminary data availability for Holt-Winters. No forecast is executed.

Weekly aggregation uses calendar weeks beginning Monday; monthly aggregation uses calendar months. Partial edge periods remain visible with their coverage but are excluded from descriptive analysis by default. Demand Explorer never expands monthly data into daily observations and never imputes missing demand.

### Compare forecasting models

After preparing a dataset:

1. Open [http://localhost:3000/forecast-lab](http://localhost:3000/forecast-lab), or use **Abrir en Laboratorio de Pronósticos** from Demand Explorer.
2. Select dataset, product, location, category, frequency, and forecast horizon.
3. Review the pre-flight panel. Partial periods are excluded; only small internal gaps (maximum two periods and at most 5% of history) may be interpolated for training, with a visible audit record.
4. Select **Ejecutar comparación**. NEXORA evaluates Naive, Seasonal Naive, Moving Average, SES, Holt, and eligible additive/multiplicative Holt-Winters models using up to five expanding-window folds.
5. Review the leaderboard, Champion rationale, WMAPE/MAE/RMSE/sMAPE/MAPE/Bias, fold ranges, α/β/γ, and the future chart with empirical 80%/95% intervals.

Forecast runs and their audit metadata are stored in local SQLite. Original and canonical datasets are never modified. Forecasting is currently univariate: future prices, promotions, weather, external signals, and inventory decisions are not used.

### Audit contextual signals

After preparing the demo dataset or another READY dataset:

1. Open [http://localhost:3000/context-radar](http://localhost:3000/context-radar).
2. Select the dataset and, when useful, a product, location, and category.
3. For the synthetic demo dataset, choose **Regenerar contexto demo** to load the fixed contextual examples.
4. Set **Disponible al corte** to inspect only what NEXORA knew at that instant. Event dates do not bypass this availability rule.
5. Select any signal to review family, event time, availability, provenance, confidence, scope, status, and deterministic match reasons.
6. Choose **Nueva señal** to register a manual signal. Manual signals are confirmed by default and never alter the demand forecast.

Demand Explorer provides **Ver contexto de esta serie**, preserving product, location, and category in the URL. Forecast Lab provides the same contextual access with an explicit notice that its current results remain univariate. Context data and audit records stay in the local SQLite database under the ignored `data/` directory.

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

See [docs/data-studio.md](docs/data-studio.md) for ingestion and readiness, [docs/demand-explorer.md](docs/demand-explorer.md) for canonical series rules, [docs/forecast-core.md](docs/forecast-core.md) for model evaluation, [docs/context-engine.md](docs/context-engine.md) for temporal safety and relevance, and [docs/architecture.md](docs/architecture.md) for broader boundaries.
