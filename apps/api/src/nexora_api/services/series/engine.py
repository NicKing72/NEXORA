"""Build compact canonical demand-series profiles from READY datasets."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import ColumnMapping, DataQualityIssue, Dataset
from nexora_api.services.data_studio.constants import NON_EXCLUSIVE_ROLES
from nexora_api.services.data_studio.quality import demand_outlier_mask
from nexora_api.services.data_studio.storage import StorageService
from nexora_api.services.series.analysis import (
    holt_winters_eligibility,
    pattern_summary,
    seasonality_advice,
    series_statistics,
    underlying_quality_statistics,
)

RequestFrequency = Literal["auto", "original", "daily", "weekly", "monthly"]
FREQUENCY_RANK = {
    "hourly": 0,
    "daily": 1,
    "weekly": 2,
    "monthly": 3,
    "quarterly": 4,
    "yearly": 5,
}
EVENT_CODES = {
    "missing": {"missing_demand", "temporal_gaps"},
    "zero": {"zero_demand"},
    "outlier": {"demand_outliers"},
    "stockout": {"possible_stockout"},
}


def _ready_dataset(db: Session, dataset_id: str) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise DataStudioError("dataset_not_found", "The requested dataset does not exist.", 404)
    if dataset.status != "ready":
        raise DataStudioError(
            "dataset_not_ready", "Only datasets marked READY can be explored.", 409
        )
    if not dataset.canonical_path:
        raise DataStudioError("dataset_not_processed", "The canonical dataset is unavailable.", 409)
    return dataset


def _role_columns(db: Session, dataset_id: str) -> dict[str, str]:
    mappings = db.query(ColumnMapping).filter(ColumnMapping.dataset_id == dataset_id).all()
    return {
        mapping.role: mapping.column_name
        for mapping in mappings
        if mapping.role not in NON_EXCLUSIVE_ROLES
    }


def _load_canonical(dataset: Dataset, storage: StorageService) -> pd.DataFrame:
    path = storage.resolve_owned_path(dataset.canonical_path or "")
    if not path.is_file():
        raise DataStudioError(
            "canonical_file_missing", "The canonical dataset file is missing.", 409
        )
    return pd.read_csv(path)


def list_ready_datasets(db: Session) -> list[dict[str, object]]:
    datasets = (
        db.query(Dataset)
        .filter(Dataset.status == "ready")
        .order_by(Dataset.ready_at.desc(), Dataset.imported_at.desc())
        .all()
    )
    return [
        {
            "id": dataset.id,
            "name": dataset.original_filename,
            "source_type": dataset.source_type,
            "row_count": dataset.row_count or 0,
            "readiness_score": dataset.readiness_score or 0,
            "frequency": dataset.frequency or "irregular",
            "ready_at": dataset.ready_at,
        }
        for dataset in datasets
    ]


def _available_frequencies(source_frequency: str) -> list[RequestFrequency]:
    result: list[RequestFrequency] = ["auto", "original"]
    source_rank = FREQUENCY_RANK.get(source_frequency)
    if source_rank is None:
        return result
    for frequency in ("daily", "weekly", "monthly"):
        if FREQUENCY_RANK[frequency] >= source_rank:
            result.append(frequency)  # type: ignore[arg-type]
    return result


def _dimension_values(series: pd.Series) -> list[dict[str, object]]:
    clean = series.dropna().astype(str)
    counts = clean.value_counts().sort_index()
    return [
        {"value": str(value), "observations": int(count)} for value, count in counts.items()
    ]


def get_series_dimensions(
    db: Session, dataset_id: str, storage: StorageService
) -> dict[str, object]:
    dataset = _ready_dataset(db, dataset_id)
    roles = _role_columns(db, dataset.id)
    if "date" not in roles or "demand" not in roles:
        raise DataStudioError("required_mapping", "DATE and DEMAND mappings are required.")
    frame = _load_canonical(dataset, storage)
    parsed_dates = pd.to_datetime(frame[roles["date"]], errors="coerce", utc=True)
    valid_dates = parsed_dates.dropna()
    products: list[dict[str, object]] = []
    product_column = roles.get("product")
    category_column = roles.get("category")
    if product_column:
        for option in _dimension_values(frame[product_column]):
            categories: list[str] = []
            if category_column:
                selected = frame[frame[product_column].astype(str) == option["value"]]
                categories = sorted(
                    selected[category_column].dropna().astype(str).unique().tolist()
                )
            products.append({**option, "categories": categories})
    source_frequency = dataset.frequency or "irregular"
    return {
        "dataset_id": dataset.id,
        "products": products,
        "locations": _dimension_values(frame[roles["location"]]) if roles.get("location") else [],
        "categories": _dimension_values(frame[roles["category"]]) if roles.get("category") else [],
        "first_date": valid_dates.min().date() if not valid_dates.empty else None,
        "last_date": valid_dates.max().date() if not valid_dates.empty else None,
        "source_frequency": source_frequency,
        "available_frequencies": _available_frequencies(source_frequency),
    }


def _resolve_frequency(source: str, requested: RequestFrequency) -> str:
    if requested in {"auto", "original"}:
        return source
    available = _available_frequencies(source)
    if requested not in available:
        raise DataStudioError(
            "frequency_too_granular",
            f"A {source} dataset cannot be expanded to {requested} resolution.",
        )
    return requested


def _period_start(dates: pd.Series, frequency: str) -> pd.Series:
    naive = dates.dt.tz_convert(None)
    if frequency == "hourly":
        return naive.dt.floor("h")
    if frequency == "daily":
        return naive.dt.normalize()
    if frequency == "weekly":
        normalized = naive.dt.normalize()
        return normalized - pd.to_timedelta(normalized.dt.weekday, unit="D")
    if frequency == "monthly":
        return naive.dt.to_period("M").dt.to_timestamp()
    if frequency == "quarterly":
        return naive.dt.to_period("Q").dt.to_timestamp()
    if frequency == "yearly":
        return naive.dt.to_period("Y").dt.to_timestamp()
    return naive


def _full_period_index(index: pd.DatetimeIndex, frequency: str) -> pd.DatetimeIndex:
    if index.empty or frequency == "irregular":
        return index
    aliases = {
        "hourly": "h",
        "daily": "D",
        "weekly": "W-MON",
        "monthly": "MS",
        "quarterly": "QS",
        "yearly": "YS",
    }
    alias = aliases.get(frequency)
    return pd.date_range(index.min(), index.max(), freq=alias) if alias else index


def _next_period_start(period: pd.Timestamp, frequency: str) -> pd.Timestamp:
    if frequency == "hourly":
        return period + pd.Timedelta(hours=1)
    if frequency == "daily":
        return period + pd.Timedelta(days=1)
    if frequency == "weekly":
        return period + pd.Timedelta(days=7)
    if frequency == "monthly":
        return period + pd.offsets.MonthBegin(1)
    if frequency == "quarterly":
        return period + pd.offsets.QuarterBegin(startingMonth=1)
    if frequency == "yearly":
        return period + pd.offsets.YearBegin(1)
    return period


def _expected_source_periods(
    period: pd.Timestamp, source_frequency: str, target_frequency: str
) -> int:
    temporal_aggregation = (
        source_frequency in FREQUENCY_RANK
        and target_frequency in FREQUENCY_RANK
        and FREQUENCY_RANK[target_frequency] > FREQUENCY_RANK[source_frequency]
    )
    if not temporal_aggregation:
        return 1
    aliases = {
        "hourly": "h",
        "daily": "D",
        "weekly": "W-MON",
        "monthly": "MS",
        "quarterly": "QS",
        "yearly": "YS",
    }
    alias = aliases[source_frequency]
    end = _next_period_start(period, target_frequency)
    return max(1, len(pd.date_range(period, end, freq=alias, inclusive="left")))


def _promotion_active(value: object) -> bool:
    if pd.isna(value):
        return False
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "si", "sí", "promo", "active"}


def _safe_number(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    return round(number, 6) if np.isfinite(number) else None


def _aggregate_periods(
    frame: pd.DataFrame,
    roles: dict[str, str],
    source_frequency: str,
    frequency: str,
) -> tuple[pd.DataFrame, str | None]:
    records: list[dict[str, object]] = []
    weighted_price_used = False
    mean_price_used = False
    price_column = roles.get("price")
    stock_column = roles.get("stock")
    promotion_column = roles.get("promotion")
    temporal_aggregation = (
        source_frequency in FREQUENCY_RANK
        and frequency in FREQUENCY_RANK
        and FREQUENCY_RANK[frequency] > FREQUENCY_RANK[source_frequency]
    )
    for period, group in frame.groupby("__period", sort=True):
        demand = group["__demand"].sum(min_count=1)
        price: float | None = None
        if price_column:
            prices = pd.to_numeric(group[price_column], errors="coerce")
            weights = group["__demand"].where(group["__demand"] > 0)
            weighted = prices.notna() & weights.notna()
            if weighted.any() and float(weights[weighted].sum()) > 0:
                price = float(np.average(prices[weighted], weights=weights[weighted]))
                weighted_price_used = True
            elif prices.notna().any():
                price = float(prices.mean())
                mean_price_used = True
        stock: float | None = None
        if stock_column:
            stock_values = pd.to_numeric(group[stock_column], errors="coerce").dropna()
            stock = float(stock_values.iloc[-1]) if not stock_values.empty else None
        promotion = None
        if promotion_column:
            promotion = bool(group[promotion_column].map(_promotion_active).any())
        expected_source_periods = _expected_source_periods(
            period, source_frequency, frequency
        )
        observed_source_periods = int(group["__source_period"].nunique())
        records.append(
            {
                "date": period,
                "demand": demand,
                "price": price,
                "stock": stock,
                "promotion": promotion,
                "source_observations": int(len(group)),
                "expected_source_periods": expected_source_periods,
                "observed_source_periods": observed_source_periods,
                **{
                    f"event_{event}": int(group[f"__event_{event}"].sum())
                    for event in EVENT_CODES
                },
            }
        )
    result = pd.DataFrame.from_records(records).set_index("date")
    full_index = _full_period_index(pd.DatetimeIndex(result.index), frequency)
    result = result.reindex(full_index)
    result["source_observations"] = result["source_observations"].fillna(0).astype(int)
    result["observed_source_periods"] = (
        result["observed_source_periods"].fillna(0).astype(int)
    )
    result["expected_source_periods"] = [
        _expected_source_periods(period, source_frequency, frequency)
        for period in result.index
    ]
    result["coverage_ratio"] = (
        result["observed_source_periods"] / result["expected_source_periods"]
    ).round(6)
    result["is_partial"] = temporal_aggregation & (
        result["observed_source_periods"] < result["expected_source_periods"]
    )
    for event in EVENT_CODES:
        result[f"event_{event}"] = result[f"event_{event}"].fillna(0).astype(int)
    if weighted_price_used and mean_price_used:
        price_method = "weighted_with_mean_fallback"
    elif weighted_price_used:
        price_method = "demand_weighted_mean"
    elif mean_price_used:
        price_method = "mean"
    else:
        price_method = None
    return result, price_method


def _date_text(value: pd.Timestamp, frequency: str) -> str:
    return value.isoformat() if frequency == "hourly" else value.strftime("%Y-%m-%d")


def _aggregation_note(
    roles: dict[str, str], product: str | None, location: str | None, source: str, resolved: str
) -> tuple[bool, str | None]:
    dimensions = (bool(roles.get("product")) and product is None) or (
        bool(roles.get("location")) and location is None
    )
    temporal = source in FREQUENCY_RANK and resolved in FREQUENCY_RANK and (
        FREQUENCY_RANK[resolved] > FREQUENCY_RANK[source]
    )
    if dimensions and temporal:
        return True, "dimensions_and_frequency"
    if dimensions:
        return True, "dimensions"
    if temporal:
        return True, "frequency"
    return False, None


def canonical_file_path(
    db: Session, dataset_id: str, storage: StorageService
) -> Path:
    """Expose the owned canonical path for non-mutating verification tests."""
    dataset = _ready_dataset(db, dataset_id)
    return storage.resolve_owned_path(dataset.canonical_path or "")


def build_series_profile(
    db: Session,
    dataset_id: str,
    storage: StorageService,
    *,
    product: str | None = None,
    location: str | None = None,
    category: str | None = None,
    frequency: RequestFrequency = "auto",
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, object]:
    dataset = _ready_dataset(db, dataset_id)
    roles = _role_columns(db, dataset.id)
    if "date" not in roles or "demand" not in roles:
        raise DataStudioError("required_mapping", "DATE and DEMAND mappings are required.")
    source_frequency = dataset.frequency or "irregular"
    resolved_frequency = _resolve_frequency(source_frequency, frequency)
    frame = _load_canonical(dataset, storage)
    frame["__date"] = pd.to_datetime(frame[roles["date"]], errors="coerce", utc=True)
    frame["__demand"] = pd.to_numeric(frame[roles["demand"]], errors="coerce")

    issue_codes = {
        code
        for (code,) in db.query(DataQualityIssue.code)
        .filter(DataQualityIssue.dataset_id == dataset.id)
        .all()
    }
    product_column = roles.get("product")
    location_column = roles.get("location")
    group_columns = [column for column in (product_column, location_column) if column]
    group_frame = frame[group_columns] if group_columns else None
    stock_column = roles.get("stock")
    numeric_stock = (
        pd.to_numeric(frame[stock_column], errors="coerce")
        if stock_column
        else pd.Series(np.nan, index=frame.index)
    )
    event_masks = {
        "missing": frame[roles["demand"]].isna(),
        "zero": frame["__demand"] == 0,
        "outlier": demand_outlier_mask(frame[roles["demand"]], group_frame),
        "stockout": (frame["__demand"] == 0) & (numeric_stock == 0),
    }
    for event, codes in EVENT_CODES.items():
        audited = bool(issue_codes & codes)
        frame[f"__event_{event}"] = event_masks[event] if audited else False

    selected = frame[frame["__date"].notna()].copy()
    filters = (
        (product_column, product),
        (location_column, location),
        (roles.get("category"), category),
    )
    for column, value in filters:
        if value is None:
            continue
        if column is None:
            raise DataStudioError("dimension_unavailable", "The requested dimension is not mapped.")
        selected = selected[selected[column].astype(str) == value]
    if start_date:
        selected = selected[selected["__date"].dt.date >= start_date]
    if end_date:
        selected = selected[selected["__date"].dt.date <= end_date]
    if selected.empty:
        raise DataStudioError("empty_series", "No observations match the selected series.", 404)

    selected = selected.sort_values("__date", kind="stable")
    selected["__source_period"] = _period_start(selected["__date"], source_frequency)
    selected["__period"] = _period_start(selected["__date"], resolved_frequency)
    aggregated, price_method = _aggregate_periods(
        selected, roles, source_frequency, resolved_frequency
    )

    event_totals = {
        event: int(aggregated[f"event_{event}"].sum()) for event in EVENT_CODES
    }
    affected_periods = {
        event: int((aggregated[f"event_{event}"] > 0).sum())
        for event in EVENT_CODES
    }
    partial_mask = aggregated["is_partial"].astype(bool)
    result_statistics = series_statistics(aggregated["demand"], partial_mask)
    result_statistics["first_date"] = _date_text(
        aggregated.index.min(), resolved_frequency
    )
    result_statistics["last_date"] = _date_text(
        aggregated.index.max(), resolved_frequency
    )
    statistics = {
        "series": result_statistics,
        "underlying_quality": underlying_quality_statistics(
            source_observations=int(aggregated["source_observations"].sum()),
            event_totals=event_totals,
            affected_periods=affected_periods,
        ),
    }
    excluded_partial_periods = int(partial_mask.sum())
    pattern_series = aggregated.loc[~partial_mask, "demand"].reset_index(drop=True)
    seasonality_series = aggregated["demand"].mask(partial_mask)
    pattern = pattern_summary(pattern_series, excluded_partial_periods)
    seasonality = seasonality_advice(
        seasonality_series, resolved_frequency, excluded_partial_periods
    )
    eligibility = holt_winters_eligibility(
        pattern_series,
        seasonality,
        total_periods=int(len(aggregated)),
        excluded_partial_periods=excluded_partial_periods,
    )
    is_aggregated, aggregation_note = _aggregation_note(
        roles, product, location, source_frequency, resolved_frequency
    )
    points = [
        {
            "date": _date_text(period, resolved_frequency),
            "demand": _safe_number(row["demand"]),
            "price": _safe_number(row["price"]),
            "stock": _safe_number(row["stock"]),
            "promotion": None if pd.isna(row["promotion"]) else bool(row["promotion"]),
            "expected_source_periods": int(row["expected_source_periods"]),
            "observed_source_periods": int(row["observed_source_periods"]),
            "coverage_ratio": _safe_number(row["coverage_ratio"]) or 0.0,
            "is_partial": bool(row["is_partial"]),
            "events": {
                event: int(row[f"event_{event}"]) for event in EVENT_CODES
            },
        }
        for period, row in aggregated.iterrows()
    ]
    return {
        "selection": {
            "dataset_id": dataset.id,
            "dataset_name": dataset.original_filename,
            "product": product,
            "location": location,
            "category": category,
            "requested_frequency": frequency,
            "resolved_frequency": resolved_frequency,
            "start_date": start_date,
            "end_date": end_date,
            "data_cutoff": selected["__date"].max().date(),
            "is_aggregated": is_aggregated,
            "aggregation_note": aggregation_note,
            "price_method": price_method,
        },
        "points": points,
        "statistics": statistics,
        "pattern": pattern,
        "seasonality": seasonality,
        "holt_winters": eligibility,
    }
