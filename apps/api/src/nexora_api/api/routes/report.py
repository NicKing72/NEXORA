"""Versioned API for immutable auditable reports and exports."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from nexora_api.db.session import get_database_session
from nexora_api.schemas.report import (
    ReportDefinitionResponse,
    ReportPreflightResponse,
    ReportRequest,
    ReportRunResponse,
    ReportRunSummary,
    ReportSectionResponse,
    ReportSourcesResponse,
    ReportSummaryResponse,
)
from nexora_api.services.reports.rendering import render_csv, render_html, render_json
from nexora_api.services.reports.service import (
    create_run,
    definitions,
    list_runs,
    preflight,
    regenerate_demo,
    require_run,
    serialize_run,
    serialize_section,
)

router = APIRouter(prefix="/api/v1/reports", tags=["reporting-engine"])


@router.get("/definitions", response_model=ReportDefinitionResponse)
def retrieve_definitions() -> dict[str, object]:
    return definitions()


@router.post("/preflight", response_model=ReportPreflightResponse)
def report_preflight(
    payload: ReportRequest, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return preflight(db, payload)


@router.post("", response_model=ReportRunResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportRequest, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_run(create_run(db, payload))


@router.post("/demo/regenerate", response_model=ReportRunResponse)
def create_demo_report(db: Session = Depends(get_database_session)) -> dict[str, object]:
    return serialize_run(regenerate_demo(db))


@router.get("", response_model=list[ReportRunSummary])
def retrieve_reports(db: Session = Depends(get_database_session)) -> list[dict[str, object]]:
    return list_runs(db)


@router.get("/{run_id}", response_model=ReportRunResponse)
def retrieve_report(run_id: UUID, db: Session = Depends(get_database_session)) -> dict[str, object]:
    return serialize_run(require_run(db, str(run_id)))


@router.get("/{run_id}/sections", response_model=list[ReportSectionResponse])
def retrieve_sections(
    run_id: UUID, db: Session = Depends(get_database_session)
) -> list[dict[str, object]]:
    run = require_run(db, str(run_id))
    ordered = sorted(run.sections, key=lambda item: item.position)
    return [serialize_section(item) for item in ordered]


@router.get("/{run_id}/sources", response_model=ReportSourcesResponse)
def retrieve_sources(
    run_id: UUID, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    run = require_run(db, str(run_id))
    return {
        "report_run_id": run.id,
        "sources": run.source_snapshot,
        "provenance": {
            "report_cutoff": run.report_cutoff,
            "calculation_version": run.calculation_version,
            "snapshot_immutable": True,
            "sources_recalculated": False,
        },
    }


@router.get("/{run_id}/summary", response_model=ReportSummaryResponse)
def retrieve_summary(
    run_id: UUID, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    run = require_run(db, str(run_id))
    return {
        "report_run_id": run.id,
        "executive_summary": run.report_payload.get("executive_summary", {}),
        "coverage": run.report_payload.get("coverage", {}),
        "warnings": run.warnings,
        "limitations": run.limitations,
    }


@router.get("/{run_id}/export")
def export_report(
    run_id: UUID,
    format: Literal["html", "json", "csv"] = Query(default="html"),
    db: Session = Depends(get_database_session),
) -> Response:
    run = require_run(db, str(run_id))
    renderers = {"html": render_html, "json": render_json, "csv": render_csv}
    media_types = {"html": "text/html", "json": "application/json", "csv": "text/csv"}
    content = renderers[format](run)
    return Response(
        content=content,
        media_type=f"{media_types[format]}; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="nexora-report-{run.id}.{format}"',
            "X-NEXORA-Report-Run": run.id,
        },
    )
