# Forecast Core v1

## Architecture

Forecast Core consumes the selected profile returned by Series Engine; it never reloads or re-aggregates source rows independently. The pipeline is:

`Canonical dataset → Series Engine → preparation → expanding-window backtesting → metrics → ranking → final fit → future forecast → persistence`

Routes remain thin. `services/forecasting/` separates preprocessing, model adapters, backtesting, metrics, ranking, empirical intervals, and orchestration. Runs are synchronous for current local volumes but use explicit status fields for a future job runner.

## Models

Candidates are Last-value Naive, Seasonal Naive, frequency-based Moving Average (daily 7, weekly 4, monthly 3), Simple Exponential Smoothing, additive Holt, additive Holt-Winters, and multiplicative Holt-Winters. `statsmodels` is the preferred smoothing engine. A deterministic NumPy fallback keeps managed Windows hosts functional when Application Control blocks SciPy native libraries; both `engine` and `parameter_source` are persisted with model parameters.

The NumPy fallback does not use fixed Holt-Winters smoothing parameters. It performs an exhaustive grid search over α, β, and γ in `{0.2, 0.4, 0.6, 0.8}` (64 candidates). The objective is minimum one-step-ahead SSE after the first seasonal cycle. Level starts at the first-cycle mean, trend at the difference between the first two cycle means divided by the period, and seasonal factors come from the first cycle. There is no iterative stopping criterion: every grid combination is evaluated, and an exact tie retains the first combination in ascending grid order. The UI identifies this as `optimized_grid_search`, which is deliberately not presented as equivalent to statsmodels continuous optimization.

Holt-Winters requires a Series Profile candidate period and at least two complete cycles. Multiplicative seasonality additionally requires strictly positive training demand. Ineligible and numerically failed candidates remain visible with a reason.

Eligibility and evaluability are separate audit concepts. `final_fit_eligible` answers whether the full prepared history satisfies a model's technical requirements. `backtest_evaluable` answers whether at least one configured expanding-window fold contains enough training history to compare that model out of sample. A weekly series with exactly 104 complete observations is therefore eligible for a final period-52 fit but not evaluable when every earlier fold contains fewer than two cycles. Persisted model results retain final-fit eligibility in `eligible` and backtesting outcome in `status`, folds, and failure reason; the API exposes both concepts explicitly.

## Training preparation

- Aggregated edge periods with `is_partial=true` are excluded and their dates recorded.
- Internal missing gaps are linearly time-interpolated only when the longest gap is at most two periods, total missingness is at most 5%, and neither edge is missing. Every affected timestamp/value is audited in the run.
- Larger or edge gaps block continuous statistical models; eligible baselines may still be evaluated.
- Zeros remain valid. Outliers and possible stockouts remain unchanged and generate warnings.
- Original and canonical files are never modified.

`data_cutoff` is the latest source date available for the selected series. `training_cutoff` is the last valid, non-partial period supplied to training. The latter is stored in the run preprocessing audit and exposed as a first-class response field. They coincide for a complete daily edge but differ when an aggregated edge period is partial.

## Temporal backtesting

Evaluation uses rolling origin with an expanding training prefix and non-overlapping validation blocks—never random splitting. Up to five folds are used. Validation horizon is `min(requested horizon, cap)`, with caps of 14 daily, 8 weekly, and 6 monthly periods. Each fold stores train/validation boundaries, observations, predictions, actuals, and metrics. Aggregated metrics are recalculated over all concatenated out-of-sample errors.

## Metrics and ranking

- `MAE = mean(|forecast − actual|)`
- `RMSE = sqrt(mean((forecast − actual)²))`
- `MAPE = mean(|error / actual|)`; null if any evaluated actual equals zero.
- `sMAPE = mean(2|error| / (|actual| + |forecast|))`; a zero/zero term contributes zero.
- `WMAPE = sum(|error|) / sum(|actual|)`; null when the denominator is zero.
- `Bias = mean(forecast − actual)`. Positive means overforecast; negative means underforecast. Bias % uses `sum(forecast − actual) / sum(actual)` when defined.

Champion selection prioritizes WMAPE. WMAPE is stored as a proportion, so the 0.5 percentage-point tolerance is `0.005`. Only models within that tolerance of the best WMAPE candidate participate in the Champion tie-break, resolved by lower absolute Bias %, lower RMSE, then greater fold stability. Similarities between lower-ranked challengers do not change the persisted Champion reason. Stability uses cross-fold WMAPE CV: high ≤10%, moderate ≤25%, otherwise low.

## Final forecast and intervals

The Champion is fitted again on all prepared history. Daily dates continue the next day, weekly dates continue Monday-start weeks, and monthly dates use calendar month starts. Empirical 80% and 95% bands add pooled out-of-sample residual quantiles to each future point. Fewer than 20 residuals produces no interval and an explicit insufficient-evidence state; these are not parametric confidence intervals.

## Persistence and limitations

SQLite stores `ForecastRun`, `ForecastModelResult`, `ForecastFoldResult`, and `ForecastPoint`. A run records UUID, series definition, horizons, UTC creation time, cutoff, preparation audit, seasonality evidence, status, Champion, warnings, metrics, ranks, folds, and future bounds. Fitted Python objects are not pickled.

Forecast Core v1 is univariate. It does not use future price, promotions, weather, competitors, news, exogenous regressors, ARIMA-family models, Prophet, Croston, machine learning, inventory optimization, or automatic decisions.
