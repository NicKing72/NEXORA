# Portfolio Engine

## Objective and boundary

Portfolio Engine answers which persisted demand series need operational attention and why. It never retrains forecasts, changes a Champion, invents inventory, calculates purchase quantities, optimizes stock, or executes logistics. The NEXORA Portfolio Priority Score is an internal diagnostic index—not a probability, financial-risk measure, SCOR standard, or purchasing recommendation.

## Architecture

- `snapshot.py` selects the latest completed Forecast Run for each stable dataset/product/location/category/frequency key available at the requested cutoff. It freezes every point and a SHA-256 digest.
- `metrics.py` calculates forecast total, average, peak, minimum, population variability, interval summaries, coverage, and projected exposure.
- `risk.py` resolves temporal operational inputs, completeness, descriptive risk, and the score.
- `ranking.py` applies stable risk/score/exposure ordering while preserving exact ties.
- `service.py` performs preflight, persistence, recovery, summaries, and the isolated demo.

`PortfolioRun` stores cutoff, version, selected Forecast Run IDs, filters, summary, warnings, and provenance. `PortfolioItem` stores the frozen metrics, operational-input states, score explanation, risk, missing inputs, and source snapshot. Forecast tables are read-only inputs.

## Metrics and missing data

For persisted forecast values \(f_t\):

- total = \(\sum f_t\);
- average = \(\sum f_t / n\);
- peak/minimum = extrema of the horizon;
- variability = population standard deviation / average when average is positive;
- coverage periods = current inventory / forecast average, only when inventory exists and average is positive.

Operational values carry `available`, `missing`, or `not_applicable`. Missing is never converted to zero. An available value with `available_at > cutoff` is excluded and audited. Projected exposure is only calculated when current and inbound inventory both exist.

## Priority Score v1

Configured components are forecast magnitude (30%), peak concentration (20%), forecast variability (20%), inventory-coverage exposure (20%), and an operational-constraint indicator (10%). Each component is normalized to 0–1. The formula is:

`100 × Σ(component × configured_weight) / Σ(weights of available components)`

Unavailable components are excluded and remaining weights are renormalized. They never contribute zero or improve the score. The result is labeled `partial` unless every component is calculable. Descriptive risk uses coverage relative to the unchanged forecast horizon: critical at ≤25%, high at ≤50%, medium below 100%, and low at or above 100%. Coverage not calculable produces `unknown`, never low. Coverage at/below lead time escalates to critical; inventory at/below declared safety stock is at least high.

Ranking order is critical, high, medium, low, unknown; then score descending, forecast total descending, and stable series key. Exact risk/score/forecast ties keep the same rank.

## Compatibility and anti-leakage

Only completed Forecast Runs with `created_at <= portfolio cutoff` can enter. Multiple historical runs for one series resolve deterministically to the most recent available run. A run never mixes points from different forecasts. Official portfolios require one dataset, frequency, and horizon; incompatible aggregation is rejected. Within one dataset the mapped demand column is treated as a common unit. Cross-dataset totals are blocked because physical-unit compatibility is not known.

## API

The versioned contract under `/api/v1/portfolio` exposes definitions, preflight, creation, listing, detail, items, summary, ranking, and `/demo/regenerate`. The demo is a deterministic Portfolio snapshot with sufficient, partial, insufficient, and tied cases. It has no Forecast Run IDs and never writes Forecast Core tables.

## Validated recovery workflows

Milestone 7A QA validated both supported sources. The deterministic demo remains decoupled from Forecast Core and recovers its six-series snapshot from Portfolio Run history after a browser reload. A real daily Forecast Run was also selected immutably, analyzed without operational inputs, and recovered after F5 with its Forecast Run ID, `portfolio_priority_v1` calculation version, missing-value states, and persisted-forecast provenance unchanged. Reopening history reads the frozen Portfolio snapshot; it does not rebuild the result from live forecast or inventory data.

## Limitations

There is no inventory ledger, optimization, EOQ, safety-stock calculation, capacity planning, purchase order, transfer, supplier decision, cost optimization, or Decision Engine integration in 7A. Operational values are optional declarations. Historical Portfolio Runs remain snapshots even when newer forecasts or inputs appear.
