"""Explainable, non-mutating data quality and readiness assessment."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC

import numpy as np
import pandas as pd
from sqlalchemy import delete
from sqlalchemy.orm import Session

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import (
    ColumnMapping,
    DataQualityIssue,
    DataQualityReport,
    Dataset,
)
from nexora_api.services.data_studio.constants import NON_EXCLUSIVE_ROLES, OPTIONAL_ROLES
from nexora_api.services.data_studio.storage import StorageService


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    count: int = 1
    column_name: str | None = None
    details: dict[str, object] = field(default_factory=dict)


def _frequency_for_dates(
    dates: pd.Series, groups: pd.DataFrame | None = None
) -> tuple[str, float, np.ndarray]:
    deltas: list[float] = []
    if groups is None or groups.empty:
        series_groups = [dates]
    else:
        working = groups.copy()
        working["__date"] = dates
        series_groups = [group["__date"] for _, group in working.groupby(list(groups.columns))]

    for group_dates in series_groups:
        ordered = pd.Series(group_dates.dropna().unique()).sort_values()
        if len(ordered) > 1:
            deltas.extend(ordered.diff().dropna().dt.total_seconds().div(3600).tolist())
    if not deltas:
        return "irregular", 0.0, np.array([], dtype=float)

    values = np.asarray(deltas, dtype=float)
    median_hours = float(np.median(values))
    ranges = {
        "hourly": (0.5, 1.5),
        "daily": (20, 28),
        "weekly": (132, 204),
        "monthly": (24 * 27, 24 * 32),
        "quarterly": (24 * 80, 24 * 100),
        "yearly": (24 * 350, 24 * 380),
    }
    detected = next(
        (name for name, (lower, upper) in ranges.items() if lower <= median_hours <= upper),
        "irregular",
    )
    if detected == "irregular":
        return detected, 0.35, values
    lower, upper = ranges[detected]
    confidence = float(((values >= lower) & (values <= upper)).mean())
    if confidence < 0.6:
        return "irregular", round(confidence, 4), values
    return detected, round(confidence, 4), values


def _expected_observations(first: pd.Timestamp, last: pd.Timestamp, frequency: str) -> int:
    duration_hours = max(0.0, (last - first).total_seconds() / 3600)
    if frequency == "hourly":
        return int(duration_hours) + 1
    if frequency == "daily":
        return int(duration_hours / 24) + 1
    if frequency == "weekly":
        return int(duration_hours / (24 * 7)) + 1
    if frequency == "monthly":
        return (last.year - first.year) * 12 + last.month - first.month + 1
    if frequency == "quarterly":
        return ((last.year - first.year) * 12 + last.month - first.month) // 3 + 1
    if frequency == "yearly":
        return last.year - first.year + 1
    return 0


def _outlier_mask(values: pd.Series, group_keys: pd.DataFrame | None = None) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    result = pd.Series(False, index=values.index)
    groups = [(None, numeric)]
    if group_keys is not None and not group_keys.empty:
        working = group_keys.copy()
        working["__value"] = numeric
        groups = [
            (key, group["__value"]) for key, group in working.groupby(list(group_keys.columns))
        ]
    for _, group in groups:
        clean = group.dropna()
        if len(clean) < 8:
            continue
        first_quartile, third_quartile = clean.quantile([0.25, 0.75])
        iqr = third_quartile - first_quartile
        if iqr > 0:
            mask = (clean < first_quartile - 1.5 * iqr) | (clean > third_quartile + 1.5 * iqr)
        else:
            median = clean.median()
            mad = (clean - median).abs().median()
            mask = (0.6745 * (clean - median).abs() / mad) > 3.5 if mad > 0 else clean != median
        result.loc[mask.index] = mask
    return result


def _score_component(value: float) -> int:
    return int(round(max(0.0, min(100.0, value))))


def run_quality_assessment(
    db: Session, dataset: Dataset, storage: StorageService
) -> DataQualityReport:
    if not dataset.canonical_path:
        raise DataStudioError("dataset_not_processed", "Select and process a dataset sheet first.")
    frame = pd.read_csv(storage.resolve_owned_path(dataset.canonical_path))
    mappings = db.query(ColumnMapping).filter(ColumnMapping.dataset_id == dataset.id).all()
    role_to_column = {
        mapping.role: mapping.column_name
        for mapping in mappings
        if mapping.role not in NON_EXCLUSIVE_ROLES
    }
    findings: list[Finding] = []
    total = len(frame)

    if total == 0:
        findings.append(Finding("ERROR", "empty_dataset", "The dataset contains no observations."))
    for required_role in ("date", "demand"):
        if required_role not in role_to_column:
            findings.append(
                Finding(
                    "ERROR",
                    f"missing_{required_role}_mapping",
                    f"Assign a column to the required {required_role.upper()} role.",
                )
            )
    if dataset.duplicate_columns:
        findings.append(
            Finding(
                "ERROR",
                "duplicate_column_names",
                "Duplicate source column names must be resolved before forecasting preparation.",
                len(dataset.duplicate_columns),
                details={"columns": dataset.duplicate_columns},
            )
        )

    date_column = role_to_column.get("date")
    demand_column = role_to_column.get("demand")
    product_column = role_to_column.get("product")
    location_column = role_to_column.get("location")
    stock_column = role_to_column.get("stock")
    group_columns = [column for column in (product_column, location_column) if column]
    group_frame = frame[group_columns] if group_columns else None

    parsed_dates = pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns, UTC]")
    missing_dates = invalid_dates = duplicate_dates = unsorted_groups = gaps = 0
    first_date = last_date = None
    frequency, frequency_confidence = "irregular", 0.0
    if date_column:
        raw_dates = frame[date_column]
        parsed_dates = pd.to_datetime(raw_dates, errors="coerce", utc=True)
        missing_dates = int(raw_dates.isna().sum())
        invalid_dates = int((raw_dates.notna() & parsed_dates.isna()).sum())
        if missing_dates:
            findings.append(
                Finding(
                    "WARNING",
                    "missing_dates",
                    f"{missing_dates} date values are missing.",
                    missing_dates,
                    date_column,
                )
            )
        if invalid_dates:
            findings.append(
                Finding(
                    "ERROR",
                    "invalid_dates",
                    f"{invalid_dates} date values could not be parsed.",
                    invalid_dates,
                    date_column,
                )
            )
        valid_dates = parsed_dates.dropna()
        if not valid_dates.empty:
            first_date = valid_dates.min()
            last_date = valid_dates.max()
            duplicate_subset = [date_column, *group_columns]
            duplicate_dates = int(
                pd.DataFrame(
                    {
                        date_column: parsed_dates,
                        **{column: frame[column] for column in group_columns},
                    }
                )
                .dropna(subset=[date_column])
                .duplicated(subset=duplicate_subset)
                .sum()
            )
            if duplicate_dates:
                findings.append(
                    Finding(
                        "WARNING",
                        "duplicate_dates",
                        f"{duplicate_dates} duplicate time keys were found.",
                        duplicate_dates,
                        date_column,
                    )
                )
            if group_columns:
                ordered_frame = frame[group_columns].copy()
                ordered_frame["__date"] = parsed_dates
                unsorted_groups = sum(
                    not group["__date"].dropna().is_monotonic_increasing
                    for _, group in ordered_frame.groupby(group_columns)
                )
            else:
                unsorted_groups = int(not valid_dates.is_monotonic_increasing)
            if unsorted_groups:
                findings.append(
                    Finding(
                        "INFO",
                        "temporal_order",
                        "Some series are not stored in chronological order.",
                        unsorted_groups,
                        date_column,
                    )
                )
            frequency, frequency_confidence, _ = _frequency_for_dates(parsed_dates, group_frame)
            if frequency == "irregular":
                findings.append(
                    Finding(
                        "WARNING",
                        "irregular_frequency",
                        "The temporal frequency is irregular or uncertain.",
                        column_name=date_column,
                    )
                )

            if frequency != "irregular":
                if group_columns:
                    temp = frame[group_columns].copy()
                    temp["__date"] = parsed_dates
                    series = [group["__date"].dropna() for _, group in temp.groupby(group_columns)]
                else:
                    series = [valid_dates]
                for dates in series:
                    unique_dates = dates.drop_duplicates()
                    if len(unique_dates) > 1:
                        gaps += max(
                            0,
                            _expected_observations(
                                unique_dates.min(), unique_dates.max(), frequency
                            )
                            - len(unique_dates),
                        )
                if gaps:
                    findings.append(
                        Finding(
                            "WARNING",
                            "temporal_gaps",
                            f"{gaps} expected time points are missing.",
                            gaps,
                            date_column,
                        )
                    )

    numeric_demand = pd.Series(np.nan, index=frame.index, dtype=float)
    missing_demand = invalid_demand = negative_demand = zero_demand = outlier_count = 0
    if demand_column:
        raw_demand = frame[demand_column]
        numeric_demand = pd.to_numeric(raw_demand, errors="coerce")
        missing_demand = int(raw_demand.isna().sum())
        invalid_demand = int((raw_demand.notna() & numeric_demand.isna()).sum())
        negative_demand = int((numeric_demand < 0).sum())
        zero_demand = int((numeric_demand == 0).sum())
        outlier_count = int(_outlier_mask(raw_demand, group_frame).sum())
        if missing_demand:
            findings.append(
                Finding(
                    "WARNING",
                    "missing_demand",
                    f"{missing_demand} demand values are missing.",
                    missing_demand,
                    demand_column,
                )
            )
        if invalid_demand:
            findings.append(
                Finding(
                    "ERROR",
                    "non_numeric_demand",
                    f"{invalid_demand} demand values are not numeric.",
                    invalid_demand,
                    demand_column,
                )
            )
        if negative_demand:
            findings.append(
                Finding(
                    "WARNING",
                    "negative_demand",
                    f"{negative_demand} negative demand values require review.",
                    negative_demand,
                    demand_column,
                )
            )
        if zero_demand:
            findings.append(
                Finding(
                    "INFO",
                    "zero_demand",
                    f"{zero_demand} zero-demand observations were found.",
                    zero_demand,
                    demand_column,
                )
            )
        if outlier_count:
            findings.append(
                Finding(
                    "WARNING",
                    "demand_outliers",
                    f"{outlier_count} potential demand outliers were flagged using IQR/MAD.",
                    outlier_count,
                    demand_column,
                    {"method": "IQR with MAD fallback"},
                )
            )

    sku_count = int(frame[product_column].nunique(dropna=True)) if product_column else 1
    location_count = int(frame[location_column].nunique(dropna=True)) if location_column else 1
    short_products = 0
    if product_column:
        product_counts = frame.groupby(product_column, dropna=True).size()
        short_threshold = 30 if frequency in {"daily", "hourly"} else 12
        short_products = int((product_counts < short_threshold).sum())
        if short_products:
            findings.append(
                Finding(
                    "WARNING",
                    "short_product_history",
                    f"{short_products} products have fewer than {short_threshold} observations.",
                    short_products,
                    product_column,
                )
            )
        findings.append(
            Finding(
                "INFO",
                "product_count",
                f"{sku_count} distinct products were detected.",
                sku_count,
                product_column,
            )
        )

    possible_stockouts = 0
    if stock_column and demand_column:
        numeric_stock = pd.to_numeric(frame[stock_column], errors="coerce")
        possible_stockouts = int(((numeric_demand == 0) & (numeric_stock == 0)).sum())
        if possible_stockouts:
            findings.append(
                Finding(
                    "WARNING",
                    "possible_stockout",
                    "Possible demand censoring caused by stockout.",
                    possible_stockouts,
                    stock_column,
                    {"rule": "demand = 0 AND stock = 0"},
                )
            )

    denominator = max(total, 1)
    structure = 100.0
    structure -= 50 if not date_column else 0
    structure -= 50 if not demand_column else 0
    structure -= 25 if dataset.duplicate_columns else 0
    structure -= 100 if total == 0 else 0
    temporal = 100.0
    temporal -= min(40, (missing_dates + invalid_dates) / denominator * 100)
    temporal -= min(35, gaps / max(total + gaps, 1) * 100)
    temporal -= 15 if frequency == "irregular" else (1 - frequency_confidence) * 15
    temporal -= min(10, duplicate_dates / denominator * 100)
    temporal -= min(10, unsorted_groups * 2)
    demand_quality = 100.0
    demand_quality -= min(55, (missing_demand + invalid_demand) / denominator * 100 * 2)
    demand_quality -= min(25, negative_demand / denominator * 100 * 2)
    demand_quality -= min(20, outlier_count / denominator * 100 * 2)
    duration_days = (
        int((last_date - first_date).days) + 1
        if first_date is not None and last_date is not None
        else 0
    )
    if duration_days >= 365:
        coverage = 100.0
    elif duration_days >= 180:
        coverage = 85.0
    elif duration_days >= 90:
        coverage = 70.0
    elif duration_days >= 30:
        coverage = 50.0
    else:
        coverage = 25.0 if total else 0.0
    coverage -= min(20, gaps / max(total + gaps, 1) * 100)
    product_coverage = (
        100.0 if not product_column else max(0.0, 100 - short_products / max(sku_count, 1) * 100)
    )
    optional_present = sum(role in role_to_column for role in OPTIONAL_ROLES)
    context = optional_present / len(OPTIONAL_ROLES) * 100

    components = {
        "structure": _score_component(structure),
        "temporal_continuity": _score_component(temporal),
        "demand_quality": _score_component(demand_quality),
        "coverage": _score_component(coverage),
        "product_coverage": _score_component(product_coverage),
        "context_availability": _score_component(context),
    }
    weights = {
        "structure": 0.25,
        "temporal_continuity": 0.25,
        "demand_quality": 0.25,
        "coverage": 0.15,
        "product_coverage": 0.05,
        "context_availability": 0.05,
    }
    readiness = int(round(sum(components[name] * weight for name, weight in weights.items())))
    deductions = [
        {
            "component": name,
            "points_lost": round((100 - components[name]) * weights[name], 2),
            "component_score": components[name],
        }
        for name in components
        if components[name] < 100
    ]
    cycles: list[str] = []
    if duration_days >= 14 and frequency in {"hourly", "daily"}:
        cycles.append(f"{duration_days // 7} potential weekly cycles")
    if duration_days >= 365:
        cycles.append(f"{max(1, duration_days // 365)} potential annual cycles")

    db.execute(delete(DataQualityIssue).where(DataQualityIssue.dataset_id == dataset.id))
    db.execute(delete(DataQualityReport).where(DataQualityReport.dataset_id == dataset.id))
    report = DataQualityReport(
        dataset_id=dataset.id,
        observations=total,
        first_date=first_date.to_pydatetime().astimezone(UTC) if first_date is not None else None,
        last_date=last_date.to_pydatetime().astimezone(UTC) if last_date is not None else None,
        duration_days=duration_days,
        frequency=frequency,
        frequency_confidence=frequency_confidence,
        sku_count=sku_count,
        location_count=location_count,
        mapped_variable_count=sum(mapping.role != "ignore" for mapping in mappings),
        readiness_score=readiness,
        component_scores=components,
        deductions=deductions,
        summary={
            "missing_dates": missing_dates,
            "temporal_gaps": gaps,
            "missing_demand": missing_demand,
            "outliers": outlier_count,
            "possible_stockouts": possible_stockouts,
            "zero_demand": zero_demand,
            "cycles": cycles,
        },
        has_critical_errors=any(finding.severity == "ERROR" for finding in findings),
    )
    db.add(report)
    db.flush()
    for finding in findings:
        db.add(
            DataQualityIssue(
                dataset_id=dataset.id,
                report_id=report.id,
                severity=finding.severity,
                code=finding.code,
                message=finding.message,
                column_name=finding.column_name,
                count=finding.count,
                details=finding.details,
            )
        )
    dataset.status = "validation_failed" if report.has_critical_errors else "validated"
    dataset.frequency = frequency
    dataset.frequency_confidence = frequency_confidence
    dataset.readiness_score = readiness
    db.commit()
    db.refresh(report)
    return report
