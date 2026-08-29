"""Deterministic canonical-role suggestions based on names, types, and samples."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime

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
from nexora_api.services.data_studio.constants import (
    CANONICAL_ROLES,
    NON_EXCLUSIVE_ROLES,
)

ROLE_ALIASES: dict[str, set[str]] = {
    "date": {"fecha", "date", "dia", "periodo", "period", "fecha_venta", "fecha_factura"},
    "demand": {
        "ventas",
        "cantidad",
        "demanda",
        "units",
        "units_sold",
        "cantidad_vendida",
        "unidades",
        "qty",
    },
    "product": {"producto", "sku", "item", "codigo", "articulo", "product_id", "cod_articulo"},
    "price": {"precio", "price", "precio_unitario", "p_unitario", "unit_price"},
    "stock": {"stock", "inventario", "inventory", "stock_actual", "on_hand"},
    "promotion": {"promocion", "promo", "campaign", "descuento", "promotion"},
    "location": {"tienda", "sucursal", "location", "store", "sede", "region"},
    "category": {"categoria", "category", "familia", "linea"},
    "cost": {"costo", "cost", "unit_cost", "costo_unitario"},
    "lead_time": {"lead_time", "tiempo_entrega", "dias_entrega"},
    "channel": {"canal", "channel", "sales_channel"},
    "supplier": {"proveedor", "supplier", "vendor"},
}
NUMERIC_ROLES = {"demand", "price", "stock", "cost", "lead_time"}
TEXT_ROLES = {"product", "location", "category", "channel", "supplier"}


def normalize_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", ascii_value.lower())).strip("_")


def _numeric_ratio(series: pd.Series) -> float:
    non_null = series.dropna()
    if non_null.empty:
        return 0.0
    return float(pd.to_numeric(non_null, errors="coerce").notna().mean())


def _date_ratio(series: pd.Series) -> float:
    non_null = series.dropna()
    if non_null.empty or pd.api.types.is_numeric_dtype(non_null):
        return 0.0
    parsed = pd.to_datetime(non_null, errors="coerce", utc=True, format="mixed")
    return float(parsed.notna().mean())


def score_column(series: pd.Series, column_name: str, role: str) -> float:
    normalized = normalize_name(column_name)
    aliases = ROLE_ALIASES[role]
    score = 0.0
    if normalized in aliases:
        score = 0.82
    elif any(alias in normalized or normalized in alias for alias in aliases if len(alias) > 2):
        score = 0.66

    numeric_ratio = _numeric_ratio(series)
    if role == "date":
        ratio = _date_ratio(series)
        score += 0.17 * ratio
        if ratio < 0.5 and normalized not in aliases:
            score *= 0.45
    elif role in NUMERIC_ROLES:
        score += 0.14 * numeric_ratio
        if numeric_ratio < 0.5 and normalized not in aliases:
            score *= 0.5
    elif role == "promotion":
        values = {normalize_name(str(value)) for value in series.dropna().head(100)}
        boolean_values = {"0", "1", "true", "false", "si", "no", "yes", "promo", "none"}
        score += 0.14 if values and values.issubset(boolean_values) else 0.0
    elif role in TEXT_ROLES:
        non_null = series.dropna()
        if not non_null.empty:
            cardinality = non_null.nunique() / len(non_null)
            score += 0.1 if 0 < cardinality < 0.8 else 0.03
    return round(min(score, 0.99), 4)


def suggest_mappings(frame: pd.DataFrame) -> list[dict[str, object]]:
    """Assign at most one source column to each canonical role."""
    candidates = [
        (score_column(frame[column], str(column), role), str(column), role)
        for column in frame.columns
        for role in CANONICAL_ROLES
    ]
    candidates.sort(reverse=True)
    assigned_columns: set[str] = set()
    assigned_roles: set[str] = set()
    suggestions: dict[str, tuple[str, float]] = {}
    for confidence, column, role in candidates:
        threshold = 0.48 if role in {"date", "demand", "product"} else 0.64
        if confidence < threshold or column in assigned_columns or role in assigned_roles:
            continue
        assigned_columns.add(column)
        assigned_roles.add(role)
        suggestions[column] = (role, confidence)

    return [
        {
            "column_name": str(column),
            "role": suggestions.get(str(column), ("ignore", 0.0))[0],
            "confidence": suggestions.get(str(column), ("ignore", 0.0))[1],
            "source": "automatic",
        }
        for column in frame.columns
    ]


def save_mappings(
    db: Session, dataset: Dataset, updates: list[dict[str, object]]
) -> list[ColumnMapping]:
    """Confirm accepted suggestions and audit actual manual changes."""
    mappings = {
        mapping.column_name: mapping
        for mapping in db.query(ColumnMapping).filter(ColumnMapping.dataset_id == dataset.id).all()
    }
    valid_columns = {column.name for column in dataset.columns}
    valid_roles = set(CANONICAL_ROLES) | set(NON_EXCLUSIVE_ROLES)
    for update in updates:
        column_name = str(update["column_name"])
        role = str(update["role"])
        if column_name not in valid_columns or column_name not in mappings:
            raise DataStudioError(
                "invalid_column", f"Column '{column_name}' is not part of the dataset."
            )
        if role not in valid_roles:
            raise DataStudioError("invalid_role", f"Role '{role}' is not supported.")
        mapping = mappings[column_name]
        if role == mapping.role:
            if mapping.source == "automatic":
                mapping.source = "confirmed"
                mapping.updated_at = datetime.now(UTC)
        else:
            mapping.role = role
            mapping.confidence = 1.0
            mapping.source = "manual"
            mapping.updated_at = datetime.now(UTC)

    exclusive_assignments = [
        mapping.role for mapping in mappings.values() if mapping.role not in NON_EXCLUSIVE_ROLES
    ]
    duplicates = sorted(
        {role for role in exclusive_assignments if exclusive_assignments.count(role) > 1}
    )
    if duplicates:
        raise DataStudioError(
            "duplicate_role",
            f"Each canonical role can be assigned once. Duplicates: {', '.join(duplicates)}.",
        )
    db.execute(delete(DataQualityIssue).where(DataQualityIssue.dataset_id == dataset.id))
    db.execute(delete(DataQualityReport).where(DataQualityReport.dataset_id == dataset.id))
    dataset.status = "mapped"
    dataset.readiness_score = None
    dataset.ready_at = None
    db.commit()
    return sorted(mappings.values(), key=lambda item: item.column_name)
