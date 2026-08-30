# Scenario Engine

## Purpose and boundary

Scenario Engine answers a conditional question: **if the user explicitly assumes these conditions, how does the trajectory differ from an immutable forecast baseline?** A scenario is not a new official forecast, does not retrain the Champion, and does not claim causality or guarantee future outcomes.

## Contracts and persistence

Every `ScenarioRun` references one completed `ForecastRun` and captures a SHA-256-protected snapshot of its persisted future points, Champion, selection, frequency, horizon, intervals, and data cutoff. `ScenarioAssumption` stores declared order, temporal window, scope, magnitude, application method, and provenance. `ScenarioPoint` stores baseline, conditional result, absolute/relative delta, original intervals, and active assumption IDs. `ScenarioAudit` is append-only lifecycle evidence.

The original `ForecastRun` and `ForecastPoint` records are never updated.

## Deterministic transformations

- Percentage, promotion, price, custom, and contextual assumptions: `current × (1 + ratio)`.
- Absolute assumption: `current + amount`.
- Supply restriction: `min(current, baseline × capacity_ratio)`. This represents potentially censored observable sales; it does not estimate lost demand.

Assumptions are applied in persisted order only to canonical forecast periods inside their inclusive date windows. Negative results are clamped to zero and audited. Overlaps are not hidden: the engine records warnings and preserves the exact active assumption IDs per point. Frequency cannot differ from the baseline, so daily, weekly, and monthly simulations do not invent granularity.

## Context evidence and anti-leakage

A contextual assumption may reference only an `estimated` `ContextImpactEstimate` whose signal scope matches the Forecast Run. The signal must have been available on or before the forecast data cutoff, and the estimate cannot use demand after that cutoff. Persisted provenance includes the signal, estimate, descriptive relative delta, Evidence Score, method, reference/event periods, historical baseline, and match reasons. Historical association is never described as causal.

## API

`/api/v1/scenarios` exposes preflight, create, execute, list, detail, assumptions, points, and compare operations. Creation freezes the baseline; execution produces deterministic points and summary totals. Re-execution starts from that same snapshot, not from a prior scenario result.

## Current limitations

There is no optimization, causal inference, automatic decision recommendation, external API input, lost-demand estimation, frequency conversion, or automatic modification of Forecast Core. Scenario assumptions are deliberately simple and user-controlled.
