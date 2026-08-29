# Data Studio — Milestone 2

Data Studio converts company CSV and Excel files into a traceable, forecast-ready data contract. It does **not** calculate forecasts or modify business values.

## Flow and storage

```text
Upload / demo → safe local source → tabular inspection → canonical CSV
              → suggested mapping → quality report → READY
```

SQLite stores dataset metadata, observed columns, canonical mappings, quality reports, individual issues, status, and lineage records. Source and canonical files remain on the local filesystem:

- `data/uploads/` — UUID-named original uploads.
- `data/processed/` — UTF-8 canonical CSV copies.
- `data/demo/` — generated demo instances.

These runtime files and `data/nexora.db` are ignored by Git. Original filenames are display metadata only; they never determine storage paths. Uploads are streamed, hashed with SHA-256, limited to 50 MB by default, and constrained beneath the configured storage root.

## Canonical roles

`date` and `demand` are required. `product` is recommended; without it, the dataset is treated as one time series. Optional roles are `price`, `stock`, `promotion`, `location`, `category`, `cost`, `lead_time`, `channel`, and `supplier`. Any remaining source column can be `external` or `ignore`.

Each canonical role is exclusive. Users can replace every automatic suggestion before validation.

## Deterministic detection

Suggestions combine:

1. Accent-insensitive, normalized column names and multilingual aliases.
2. Numeric, textual, Boolean-like, and date-parsing ratios.
3. Sample cardinality and observed values.
4. A greedy uniqueness rule that prevents one column or role from being selected twice.

Confidence is a heuristic score, not a probability. No external AI API is used.

Frequency detection evaluates within-series timestamp deltas and supports hourly, daily, weekly, monthly, quarterly, yearly, and irregular histories. Outliers use per-series IQR, with MAD robust-z fallback when IQR is zero. Values are flagged only; they are never removed.

Possible stockouts use the cautious rule `demand = 0 AND stock = 0` and are reported as “Possible demand censoring caused by stockout.” A zero demand value with positive stock is not classified the same way.

## Data Readiness Score

Every component is scored from 0 to 100, then combined deterministically:

| Component | Weight | Main deductions |
| --- | ---: | --- |
| Structure | 25% | Missing required mappings, empty data, duplicate headers |
| Temporal continuity | 25% | Invalid/missing dates, gaps, duplicates, irregularity, ordering |
| Demand quality | 25% | Missing/non-numeric demand, negatives, robust outliers |
| Coverage | 15% | Short history and temporal gaps |
| Product coverage | 5% | Products with insufficient observations |
| Context availability | 5% | Optional canonical context not present |

The UI exposes every component score and its weighted point loss. Warnings do not block READY; critical `ERROR` findings do.

## Demo dataset

Seed `2042` generates 731 daily dates from 2024-01-01 through 2025-12-31, eight products, two categories, and two locations (11,696 rows). It includes heterogeneous baselines, moderate trends, weekly and annual cycles, promotions, price movement, 24 stockout candidates, 12 missing demand values, 10 missing prices, and 14 injected demand outliers. The same content always produces the same SHA-256 hash.

## Current limitations

- Formulas are read as stored values; Data Studio never executes workbook content.
- Password-protected workbooks are not supported.
- `.xls` uses `xlrd`; `.xlsx` uses `openpyxl`.
- Duplicate headers are reported as critical because tabular parsers must disambiguate them technically.
- No cleaning policy, forecasting, automatic correction, authentication, or cloud storage exists in this milestone.
- Table creation follows the existing `create_all` foundation. Introduce versioned migrations before production deployment.
