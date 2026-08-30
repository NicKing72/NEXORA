# Context Impact & Evidence Engine

Milestone 4B estimates descriptive associations between contextual signals and observed demand. An **observed impact** is the difference between demand during an event and a locally comparable historical baseline. It is not a causal estimate and never modifies Forecast Core.

## Evidence preparation and baseline

The engine requests a canonical, scope-filtered series from Series Engine and preserves its aggregation, missing values, outlier flags, stockout flags, coverage, and partial-period metadata. It never edits the original or canonical file.

- Daily: each event day is compared with the same weekday from up to eight prior weeks.
- Weekly: up to eight complete prior weeks form the baseline.
- Monthly: up to six complete prior calendar months form the baseline.

The event itself and partial periods are excluded from reference data. Missing values are not imputed; flagged outliers remain in the calculation and are disclosed. The reported values are means per canonical period:

```text
absolute_delta = observed_mean - baseline_mean
relative_delta = absolute_delta / baseline_mean
```

A zero or invalid baseline produces no relative percentage and is marked as insufficient evidence.

## Evidence score

The deterministic `context_evidence_v1` score ranges from 0 to 100:

```text
25 × min(reference periods / 8, 1)
+ 25 × valid event periods / expected event periods
+ 20 × (1 - contaminated periods / evaluated periods)
+ 15 × min(compatible historical events / 3, 1)
+ 15 × signal confidence (0.5 when not supplied)
```

Levels are insufficient `<40`, low `40–59.99`, moderate `60–79.99`, and high `≥80`. Fewer than three reference periods always yields `insufficient_evidence`. The persisted breakdown exposes every component.

## Temporal safety

Three cutoffs retain different meanings: `event_start/event_end` describe occurrence, `available_at` describes when NEXORA knew the signal, and `data_cutoff` limits observed demand. An estimate requested with an availability cutoff cannot use a signal learned later. Events after the demand cutoff are `not_observable`; unfinished events are `pending`.

## Stockouts and analogies

Stockout sales may be censored by unavailable inventory. NEXORA can preserve baseline and observed values for audit, but records the result as `not_observable`, uses direction `unknown`, and never transfers it to a future analogy.

Future analogies require at least one earlier `estimated` signal with the same dataset, family, type, scope type, and every explicit dimension. The historical estimate's demand cutoff must also be no later than the future signal's `available_at`, preventing later outcomes from leaking into an earlier knowledge state. The API reports the historical minimum, median, and maximum relative differences; with one event those three values coincide and the sample count remains explicit. This range is descriptive and is not applied to a forecast.

## Persistence and API

Each estimation appends an immutable `ContextImpactEstimate` containing inputs, method, scope, cutoffs, values, direction, evidence score, quality summary, reason, and timestamp. Re-estimation preserves earlier revisions while list/detail queries return the latest revision per signal.

- `GET /api/v1/context-impact/signals/{id}`
- `POST /api/v1/context-impact/signals/{id}/estimate`
- `GET /api/v1/context-impact/signals/{id}/analogies`
- `GET /api/v1/context-impact/datasets/{dataset_id}`
- `POST /api/v1/context-impact/datasets/{dataset_id}/estimate`

## Limitations

The baseline is descriptive, not causal or experimental. It does not control for every overlapping event, trend break, price change, or selection bias; overlaps are disclosed as contamination. There is no external ingestion, scraping, LLM, ML, SARIMAX, scenario execution, or contextual forecast adjustment in 4B.
