"""Dataset registration and canonical technical parsing workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pandas as pd
from fastapi import UploadFile
from sqlalchemy import delete
from sqlalchemy.orm import Session

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import (
    ColumnMapping,
    DataQualityIssue,
    DataQualityReport,
    Dataset,
    DatasetColumn,
    DataTransformation,
)
from nexora_api.services.data_studio.demo import build_demo_csv
from nexora_api.services.data_studio.mapping import normalize_name, suggest_mappings
from nexora_api.services.data_studio.storage import StorageService, StoredFile
from nexora_api.services.data_studio.tabular import json_safe_value, parse_tabular


def _create_dataset(stored: StoredFile, source_type: str) -> Dataset:
    return Dataset(
        id=stored.relative_path.split("/")[-1].split(".")[0],
        original_filename=stored.original_filename,
        stored_path=stored.relative_path,
        source_type=source_type,
        file_type=stored.file_type,
        mime_type=stored.mime_type,
        file_size=stored.size,
        sha256=stored.sha256,
        status="uploaded",
        imported_at=datetime.now(UTC),
    )


def _column_record(dataset_id: str, column: str, series: pd.Series, position: int) -> DatasetColumn:
    return DatasetColumn(
        dataset_id=dataset_id,
        name=column,
        normalized_name=normalize_name(column),
        data_type=str(series.dtype),
        position=position,
        null_count=int(series.isna().sum()),
        unique_count=int(series.nunique(dropna=True)),
        sample_values=[json_safe_value(value) for value in series.dropna().head(5)],
    )


def process_dataset(
    db: Session, dataset: Dataset, storage: StorageService, selected_sheet: str | None = None
) -> Dataset:
    path = storage.resolve_owned_path(dataset.stored_path)
    tabular = parse_tabular(path, dataset.file_type, selected_sheet)

    db.execute(delete(DataQualityIssue).where(DataQualityIssue.dataset_id == dataset.id))
    db.execute(delete(DataQualityReport).where(DataQualityReport.dataset_id == dataset.id))
    db.execute(delete(ColumnMapping).where(ColumnMapping.dataset_id == dataset.id))
    db.execute(delete(DatasetColumn).where(DatasetColumn.dataset_id == dataset.id))

    dataset.row_count = len(tabular.frame)
    dataset.column_count = len(tabular.frame.columns)
    dataset.available_sheets = tabular.available_sheets
    dataset.selected_sheet = tabular.selected_sheet
    dataset.duplicate_columns = tabular.duplicate_columns
    dataset.status = "inspected"
    dataset.readiness_score = None
    dataset.ready_at = None
    canonical_content = tabular.frame.to_csv(index=False, lineterminator="\n")
    dataset.canonical_path = storage.write_processed_csv(canonical_content, dataset.id)

    for position, column in enumerate(tabular.frame.columns):
        db.add(_column_record(dataset.id, str(column), tabular.frame[column], position))
    for suggestion in suggest_mappings(tabular.frame):
        db.add(ColumnMapping(dataset_id=dataset.id, **suggestion))
    db.add(
        DataTransformation(
            dataset_id=dataset.id,
            original_value=dataset.stored_path,
            transformed_value=dataset.canonical_path,
            method="technical_canonicalization",
            reason=(
                "Parsed the selected tabular source into a UTF-8 canonical CSV "
                "without business-value cleaning."
            ),
        )
    )
    db.commit()
    db.refresh(dataset)
    return dataset


async def ingest_upload(
    db: Session,
    storage: StorageService,
    upload: UploadFile,
    selected_sheet: str | None = None,
) -> Dataset:
    dataset_id = str(uuid4())
    stored = await storage.save_upload(upload, dataset_id)
    dataset = _create_dataset(stored, "upload")
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    try:
        if dataset.file_type in {"xlsx", "xls"}:
            from nexora_api.services.data_studio.tabular import inspect_excel_sheets

            sheets = inspect_excel_sheets(
                storage.resolve_owned_path(dataset.stored_path), dataset.file_type
            )
            dataset.available_sheets = sheets
            if selected_sheet is None and len(sheets) > 1:
                dataset.status = "awaiting_sheet"
                db.commit()
                db.refresh(dataset)
                return dataset
        return process_dataset(db, dataset, storage, selected_sheet)
    except Exception:
        db.delete(dataset)
        db.commit()
        storage.remove_owned_file(stored.relative_path)
        raise


def ingest_demo(db: Session, storage: StorageService) -> Dataset:
    dataset_id = str(uuid4())
    stored = storage.save_demo_bytes(build_demo_csv(), dataset_id)
    dataset = _create_dataset(stored, "demo")
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return process_dataset(db, dataset, storage)


def get_dataset_or_raise(db: Session, dataset_id: str) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise DataStudioError("dataset_not_found", "The requested dataset does not exist.", 404)
    return dataset
