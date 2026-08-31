# NEXORA — Demand Intelligence System

NEXORA is a professional demand-intelligence workspace. It combines auditable data preparation, univariate forecasting, contextual evidence, conditional scenarios, and deterministic decision support. Recommendations never execute actions, modify forecasts, or claim causality.

## What is included

- **Web application:** Next.js, strict TypeScript, Tailwind CSS, responsive navigation.
- **API:** Python, FastAPI, typed schemas, modular routes and services.
- **Data Studio:** CSV, XLSX, and XLS import; demo data; mapping; quality audit; readiness score.
- **Demand Explorer:** product, location, category, date, and frequency filters; interactive history; quality markers; descriptive pattern analysis.
- **Forecast Lab:** explicit training preparation, seven statistical candidates, temporal backtesting, auditable Champion ranking, empirical intervals, and persisted runs.
- **Context Radar:** manual and reproducible demo signals, deterministic scope matching, provenance, anti-leakage cutoffs, observed-impact evidence, and strict-scope historical analogies.
- **Scenario Lab:** conditional, auditable simulations over an immutable official Forecast Run.
- **Decision Center:** ranked recommendations with evidence, limitations, lifecycle, provenance, optional baseline-versus-scenario comparison, and optional frozen SCOR evidence.
- **SCOR Diagnostic:** auditable six-month KPI calculations for PLAN, SOURCE, MAKE, DELIVER, and RETURN, with optional company targets and cautious critical-link prioritization.
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
6. Choose **Estimar evidencia** to compare a historical event with its local temporal baseline. Review baseline, observed demand, evidence score, method, contamination, and insufficiency reasons.
7. Future signals show a descriptive historical range when a compatible prior estimate exists, with the exact sample count visible. Stockouts are marked as potentially censored and never transferred as expected demand impact.
8. Choose **Nueva señal** to register a manual signal. Manual signals are confirmed by default and never alter the demand forecast.

Demand Explorer provides **Ver contexto de esta serie**, preserving product, location, and category in the URL. Forecast Lab provides the same contextual access with an explicit notice that its current results remain univariate. Context data and audit records stay in the local SQLite database under the ignored `data/` directory.

### Simulate conditional scenarios

After completing at least one Forecast Run:

1. Open [http://localhost:3000/scenario-lab](http://localhost:3000/scenario-lab).
2. Select the persisted Forecast Run that will remain the immutable baseline.
3. Add one or more assumptions, choose their dates, and declare a percentage, absolute amount, promotion, price change, supply restriction, custom condition, or eligible historical context evidence.
4. Select **Ejecutar simulación** to compare baseline and conditional trajectories, original intervals, total delta, affected periods, warnings, and provenance.
5. Reopen stored scenarios from the history area to recover exactly what was simulated.

Scenario Engine applies assumptions in their visible order and never retrains or overwrites the Champion. Supply restrictions represent potentially censored sales rather than invented lost demand. Historical context evidence remains descriptive, subject to cutoff protection, and does not prove causality. Simulations do not guarantee future results.

### Review decision support

After completing a Forecast Run, with an optional stored scenario:

1. Open [http://localhost:3000/decision-center](http://localhost:3000/decision-center).
2. Select the official Forecast Run, decision cutoff, optional hypothetical scenario, and—when available—an optional compatible SCOR diagnostic.
3. Review preflight inputs and select **Generar recomendaciones**.
4. Inspect priority, support, evidence, limitations, and provenance for each recommendation. SCOR badges distinguish recommendations that originate from a gap, are reinforced by it, or request missing evidence.
5. When a scenario is present, compare it with the immutable official baseline; it never becomes the official forecast.
6. Open **Evidencia SCOR utilizada** to audit the frozen KPI result, target, gap, coverage, period, source, and calculation version.
7. Change a recommendation lifecycle state when reviewed, then reload to confirm persistence.

Decision Engine does not execute orders or calculate optimal quantities. Inventory position, lead time, MOQ, costs, and service targets are explicitly listed as missing whenever they are unavailable. Contextual associations remain descriptive rather than causal.

### Run a quantitative SCOR diagnostic

1. Open [http://localhost:3000/scor-diagnostic](http://localhost:3000/scor-diagnostic).
2. Choose **Regenerar demo** to create the reproducible six-month assessment, or **Nuevo diagnóstico** to enter raw company aggregates.
3. Select **Calcular indicadores** and inspect the process map, KPI matrix, original inputs, substituted formula, evidence state, source, and engine version.
4. Select a configured benchmark profile to evaluate optional gaps. The controlled tie profile demonstrates that NEXORA never forces a winner.
5. Use **Analizar en Centro de Decisiones** to carry the selected diagnosis without duplicating its data.
6. Reload the page to recover the persisted assessment and audit trail.

NEXORA preserves missing inputs and zero denominators as explicit evidence states. For monthly ratios it divides the six-month sum of numerators by the sum of denominators; it never averages monthly percentages. The NEXORA Gap Score is an internal, explainable distance-to-target measure—not an official SCOR score. This milestone does not optimize logistics or change forecasts.

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

See [docs/data-studio.md](docs/data-studio.md) for ingestion and readiness, [docs/demand-explorer.md](docs/demand-explorer.md) for canonical series rules, [docs/forecast-core.md](docs/forecast-core.md) for model evaluation, [docs/context-engine.md](docs/context-engine.md) for signal contracts, [docs/context-impact.md](docs/context-impact.md) for evidence methodology, [docs/scenario-engine.md](docs/scenario-engine.md) for conditional simulation rules, [docs/decision-engine.md](docs/decision-engine.md) for recommendation rules, [docs/scor-engine.md](docs/scor-engine.md) for quantitative chain diagnostics, [docs/scor-decision-integration.md](docs/scor-decision-integration.md) for the versioned SCOR support contract, and [docs/architecture.md](docs/architecture.md) for broader boundaries.
