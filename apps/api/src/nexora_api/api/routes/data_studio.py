"""Versioned REST endpoints for the Data Studio workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from nexora_api.core.config import get_settings
from nexora_api.core.exceptions import DataStudioError
from nexora_api.db.session import get_database_session
from nexora_api.models.dataset import ColumnMapping, DataQualityIssue, DataQualityReport, Dataset
from nexora_api.schemas.data_studio import (
    ColumnMappingResponse,
    DatasetPreviewResponse,
    DatasetResponse,
    MappingUpdateRequest,
    QualityAssessmentResponse,
    QualityIssueResponse,
    QualityReportResponse,
    ReadyResponse,
    SheetListResponse,
    SheetSelection,
)
from nexora_api.services.data_studio.ingestion import (
    get_dataset_or_raise,
    ingest_demo,
    ingest_upload,
    process_dataset,
)
from nexora_api.services.data_studio.mapping import save_mappings
from nexora_api.services.data_studio.quality import run_quality_assessment
from nexora_api.services.data_studio.storage import StorageService
from nexora_api.services.data_studio.tabular import preview_records

router = APIRouter(prefix="/api/v1/datasets", tags=["data-studio"])


@lru_cache
def get_storage_service() -> StorageService:
    settings = get_settings()
    return StorageService(settings.storage_root, settings.max_upload_bytes)


@router.post("/upload", response_model=DatasetResponse, status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    selected_sheet: str | None = Form(None),
    db: Session = Depends(get_database_session),
    storage: StorageService = Depends(get_storage_service),
) -> Dataset:
    return await ingest_upload(db, storage, file, selected_sheet)


@router.post("/demo", response_model=DatasetResponse, status_code=201)
def load_demo_dataset(
    db: Session = Depends(get_database_session),
    storage: StorageService = Depends(get_storage_service),
) -> Dataset:
    return ingest_demo(db, storage)


@router.get("/{dataset_id}", response_model=DatasetResponse)
def retrieve_dataset(dataset_id: str, db: Session = Depends(get_database_session)) -> Dataset:
    return get_dataset_or_raise(db, dataset_id)


@router.get("/{dataset_id}/sheets", response_model=SheetListResponse)
def retrieve_sheets(
    dataset_id: str, db: Session = Depends(get_database_session)
) -> SheetListResponse:
    dataset = get_dataset_or_raise(db, dataset_id)
    return SheetListResponse(
        dataset_id=dataset.id,
        selected_sheet=dataset.selected_sheet,
        sheets=dataset.available_sheets,
    )


@router.post("/{dataset_id}/sheet", response_model=DatasetResponse)
def select_sheet(
    dataset_id: str,
    request: SheetSelection,
    db: Session = Depends(get_database_session),
    storage: StorageService = Depends(get_storage_service),
) -> Dataset:
    dataset = get_dataset_or_raise(db, dataset_id)
    if dataset.file_type not in {"xlsx", "xls"}:
        raise DataStudioError("not_excel", "Sheet selection is available only for Excel files.")
    return process_dataset(db, dataset, storage, request.sheet)


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def preview_dataset(
    dataset_id: str,
    limit: int = Query(30, ge=1, le=50),
    db: Session = Depends(get_database_session),
    storage: StorageService = Depends(get_storage_service),
) -> DatasetPreviewResponse:
    dataset = get_dataset_or_raise(db, dataset_id)
    if not dataset.canonical_path:
        raise DataStudioError(
            "dataset_not_processed", "Select an Excel sheet before previewing data."
        )
    frame = pd.read_csv(storage.resolve_owned_path(dataset.canonical_path))
    return DatasetPreviewResponse(
        dataset_id=dataset.id,
        columns=[str(column) for column in frame.columns],
        rows=preview_records(frame, limit),
        total_rows=len(frame),
    )


@router.get("/{dataset_id}/mappings", response_model=list[ColumnMappingResponse])
def retrieve_mappings(
    dataset_id: str, db: Session = Depends(get_database_session)
) -> list[ColumnMapping]:
    get_dataset_or_raise(db, dataset_id)
    return (
        db.query(ColumnMapping)
        .filter(ColumnMapping.dataset_id == dataset_id)
        .order_by(ColumnMapping.column_name)
        .all()
    )


@router.put("/{dataset_id}/mappings", response_model=list[ColumnMappingResponse])
def update_mappings(
    dataset_id: str,
    request: MappingUpdateRequest,
    db: Session = Depends(get_database_session),
) -> list[ColumnMapping]:
    dataset = get_dataset_or_raise(db, dataset_id)
    return save_mappings(db, dataset, [mapping.dict() for mapping in request.mappings])


def _quality_response(db: Session, report: DataQualityReport) -> QualityAssessmentResponse:
    issues = (
        db.query(DataQualityIssue)
        .filter(DataQualityIssue.report_id == report.id)
        .order_by(DataQualityIssue.severity, DataQualityIssue.code)
        .all()
    )
    return QualityAssessmentResponse(
        report=QualityReportResponse.from_orm(report),
        issues=[QualityIssueResponse.from_orm(issue) for issue in issues],
    )


@router.post("/{dataset_id}/validate", response_model=QualityAssessmentResponse)
def validate_dataset(
    dataset_id: str,
    db: Session = Depends(get_database_session),
    storage: StorageService = Depends(get_storage_service),
) -> QualityAssessmentResponse:
    dataset = get_dataset_or_raise(db, dataset_id)
    return _quality_response(db, run_quality_assessment(db, dataset, storage))


@router.get("/{dataset_id}/quality-report", response_model=QualityAssessmentResponse)
def retrieve_quality_report(
    dataset_id: str, db: Session = Depends(get_database_session)
) -> QualityAssessmentResponse:
    get_dataset_or_raise(db, dataset_id)
    report = (
        db.query(DataQualityReport).filter(DataQualityReport.dataset_id == dataset_id).one_or_none()
    )
    if report is None:
        raise DataStudioError(
            "report_not_found", "Run validation before requesting a quality report.", 404
        )
    return _quality_response(db, report)


@router.get("/{dataset_id}/quality-issues", response_model=list[QualityIssueResponse])
def retrieve_quality_issues(
    dataset_id: str,
    severity: str | None = Query(None, pattern="^(ERROR|WARNING|INFO)$"),
    db: Session = Depends(get_database_session),
) -> list[DataQualityIssue]:
    get_dataset_or_raise(db, dataset_id)
    query = db.query(DataQualityIssue).filter(DataQualityIssue.dataset_id == dataset_id)
    if severity:
        query = query.filter(DataQualityIssue.severity == severity)
    return query.order_by(DataQualityIssue.severity, DataQualityIssue.code).all()


@router.post("/{dataset_id}/ready", response_model=ReadyResponse)
def mark_dataset_ready(
    dataset_id: str, db: Session = Depends(get_database_session)
) -> ReadyResponse:
    dataset = get_dataset_or_raise(db, dataset_id)
    report = (
        db.query(DataQualityReport).filter(DataQualityReport.dataset_id == dataset_id).one_or_none()
    )
    if report is None:
        raise DataStudioError(
            "validation_required", "Run data quality validation before marking ready."
        )
    if report.has_critical_errors:
        raise DataStudioError(
            "critical_issues", "Resolve critical data issues before continuing to READY."
        )
    roles = {
        mapping.role
        for mapping in db.query(ColumnMapping).filter(ColumnMapping.dataset_id == dataset_id).all()
    }
    if not {"date", "demand"}.issubset(roles):
        raise DataStudioError("required_mapping", "DATE and DEMAND mappings are required.")
    dataset.status = "ready"
    dataset.ready_at = datetime.now(UTC)
    db.commit()
    db.refresh(dataset)
    quality = _quality_response(db, report)
    return ReadyResponse(dataset=DatasetResponse.from_orm(dataset), **quality.dict())
