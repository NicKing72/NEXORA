# Demand Explorer and Series Engine

## Data flow

Demand Explorer lists only datasets whose metadata status is `ready`. The browser requests dimensions and a compact series profile from `/api/v1/series/`; the API resolves the owned canonical CSV stored by Data Studio. Original uploads and canonical files are read-only during exploration, and individual explorations are not persisted.

A series is defined by time plus the mapped dimensions in scope. The canonical uniqueness key is `date + product + location` when those mappings exist. Therefore, two products observed on the same date are separate observations, not duplicate dates.

## Filtering and aggregation

Filters support product, location, category, inclusive date range, and frequency. Omitting product or location means “all” and produces an explicitly labeled aggregate series.

- Demand is summed per period.
- Price uses a demand-weighted mean when positive demand provides safe weights; otherwise it uses the arithmetic mean.
- Stock uses the last non-null value in the period.
- Promotion is active when any observation in the period is active.
- Categories remain dimensions and are never averaged.

Weekly periods begin on Monday and end on Sunday. Monthly periods are calendar months. The engine permits only equal or coarser resolution than the source: daily data may become weekly or monthly, while monthly data cannot become daily. Missing periods remain null; there is no interpolation, deletion, or imputation.

Every resulting point records expected and observed source periods, a coverage ratio, and whether the period is partial. For example, a Monday–Sunday week ending after the dataset boundary can report `3 / 7`, `0.428571`, and `is_partial = true`. The demand sum remains visible for lineage, but partial periods are excluded by default from distribution metrics, pattern analysis, seasonality evidence, and model-data eligibility. Original-resolution periods are not labeled partial.

## Quality events and statistics

Markers are exposed only for issue types present in the stored Data Studio audit. Missing demand, zero demand, possible stockouts, and demand outliers therefore share the audit's rules. The outlier mask reuses the existing IQR/MAD implementation and possible stockout remains the prudent condition `demand = 0 AND stock = 0`.

Quality events are consolidated into one count per event type and resulting period. A weekly marker can therefore report several source outliers or stockouts without drawing overlapping markers, while preserving the source count in the tooltip.

Statistics have two explicit levels. **Resulting series** reports periods, complete/partial coverage, completely missing periods, zero-demand periods, range, total, and distribution metrics. Total demand includes every visible period; mean, median, extremes, population standard deviation, and coefficient of variation (`std / mean`) exclude partial periods. **Underlying quality** reports selected source rows, missing demand values, zero-demand rows, audited outliers, possible stockouts, and how many resulting periods each issue type affects. CV is null when the complete-period mean is zero.

## Descriptive pattern rules

Trend is the least-squares slope over complete observed positions. Its approximate full-window change is normalized by absolute mean demand. Absolute change below 3% is stable; 3% to below 10% is slight; 10% to below 25% is moderate; and 25% or more is strong. Direction is retained, producing labels such as `increasing_slight` and `decreasing_moderate`. Volatility uses absolute CV: below 0.25 is low, below 0.50 is moderate, otherwise high.

Intermittence reports the zero-period percentage and ADI: observed non-null periods divided by positive-demand periods. ADI above 1.32 is labeled as an intermittence signal. These labels are descriptive and do not claim causality.

The Seasonality Advisor evaluates lag autocorrelation at a frequency-specific candidate: 7 daily, 52 weekly, 12 monthly, or 4 quarterly periods. At least the larger of eight or one candidate period of paired observations is required. Correlation ≥0.60 is high evidence, ≥0.35 moderate, and lower evidence remains inconclusive.

Preliminary Holt-Winters compatibility checks technical data availability only: a supported candidate and at least two complete, non-partial candidate cycles. Recommendation is separate: it is favorable for evaluation only with high seasonal evidence and at least three cycles; otherwise technical compatibility is labeled limited. This does not assert that Holt-Winters is the best model. It does not train, fit, score, or forecast, and missing values are reported for later treatment.

## Current limits

Profiles are computed on demand with pandas and are appropriate for the current local dataset scale. Irregular sources keep original resolution. The engine does not estimate lost demand, correct outliers, infer causality, create future dates, or run a forecasting algorithm.
