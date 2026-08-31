"""Orchestrate immutable report preflight, persistence, history, and demo."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.report import ReportRun, ReportSection
from nexora_api.schemas.report import ReportRequest
from nexora_api.services.reports import REPORT_VERSION, SOURCE_LAYERS
from nexora_api.services.reports.compatibility import resolve_sources
from nexora_api.services.reports.executive import build_executive_summary
from nexora_api.services.reports.sections import build_sections
from nexora_api.services.reports.snapshot import freeze_sources

DEMO_REPORT_ID = str(uuid5(NAMESPACE_URL, "nexora/reports/demo/v1"))

REPORT_TYPES = [
    {"key": "integrated", "label": "Reporte ejecutivo integrado", "required": ["forecast"]},
    {"key": "forecast", "label": "Reporte de pronóstico", "required": ["forecast"]},
    {"key": "decisions", "label": "Reporte de decisiones", "required": ["forecast", "decision"]},
    {"key": "scor", "label": "Reporte SCOR", "required": ["scor"]},
    {"key": "portfolio", "label": "Reporte de Portafolio", "required": ["portfolio"]},
]


def definitions() -> dict[str, object]:
    return {
        "calculation_version": REPORT_VERSION,
        "report_types": REPORT_TYPES,
        "source_layers": list(SOURCE_LAYERS),
        "export_formats": ["html", "json", "csv"],
        "boundaries": [
            "no_forecast_recalculation",
            "no_source_mutation",
            "missing_is_not_zero",
            "no_causal_claims",
            "report_is_not_execution",
        ],
    }


def _coverage(sources: dict[str, object]) -> dict[str, object]:
    included = [key for key in SOURCE_LAYERS if sources.get(key) is not None]
    count = len(included)
    status = "complete" if count == len(SOURCE_LAYERS) else "partial" if count else "insufficient"
    return {
        "included": count,
        "total": len(SOURCE_LAYERS),
        "ratio": round(count / len(SOURCE_LAYERS), 4),
        "status": status,
        "included_layers": included,
        "missing_layers": [key for key in SOURCE_LAYERS if key not in included],
        "meaning": "source_coverage_not_probability",
    }


def _scope(sources: dict[str, object]) -> dict[str, object]:
    forecast = sources.get("forecast")
    if isinstance(forecast, dict):
        selection = forecast.get("selection")
        return {
            **(selection if isinstance(selection, dict) else {}),
            "frequency": forecast.get("frequency"),
            "horizon": forecast.get("horizon"),
        }
    return {}


def _limitations(sources: dict[str, object]) -> list[str]:
    values = ["Los datos faltantes permanecen faltantes y nunca se convierten en cero."]
    if sources.get("forecast"):
        values.append("El forecast no garantiza demanda futura.")
    if sources.get("scenario"):
        values.append("El escenario es hipotético y no modifica el forecast oficial.")
    if sources.get("scor"):
        values.append("SCOR describe brechas bajo las métricas y metas configuradas.")
    if sources.get("portfolio"):
        values.append("Portafolio prioriza revisión y no calcula cantidades óptimas.")
    if sources.get("decision"):
        values.append("Decision Center recomienda revisiones; no ejecuta órdenes.")
    if sources.get("explanation"):
        values.append("Explanation reconstruye evidencia; no crea causalidad.")
    return values


def _prepare(db: Session, payload: ReportRequest) -> dict[str, object]:
    resolved = resolve_sources(db, **payload.dict(exclude={"title"}))
    sources = freeze_sources(db, resolved)
    coverage = _coverage(sources)
    limitations = _limitations(sources)
    warnings = [f"source_not_included:{key}" for key in coverage["missing_layers"]]
    return {
        "resolved": resolved,
        "sources": sources,
        "coverage": coverage,
        "limitations": limitations,
        "warnings": warnings,
        "scope": _scope(sources),
        "dataset_id": resolved["dataset_id"],
    }


def preflight(db: Session, payload: ReportRequest) -> dict[str, object]:
    prepared = _prepare(db, payload)
    return {
        "report_type": payload.report_type,
        "report_cutoff": payload.report_cutoff,
        "dataset_id": prepared["dataset_id"],
        "scope": prepared["scope"],
        "sources": {
            key: {
                "included": prepared["sources"].get(key) is not None,
                "id": (
                    prepared["sources"][key].get("id")
                    if isinstance(prepared["sources"].get(key), dict)
                    else None
                ),
            }
            for key in SOURCE_LAYERS
        },
        "coverage": prepared["coverage"],
        "warnings": prepared["warnings"],
        "limitations": prepared["limitations"],
        "ready": True,
    }


def _persist(
    db: Session,
    *,
    run_id: str,
    payload: ReportRequest,
    sources: dict[str, object],
    coverage: dict[str, object],
    limitations: list[str],
    warnings: list[str],
    dataset_id: str | None,
    is_demo: bool = False,
) -> ReportRun:
    cutoff_text = payload.report_cutoff.isoformat()
    sections = build_sections(
        report_type=payload.report_type,
        title=payload.title,
        cutoff=cutoff_text,
        sources=sources,
        coverage=coverage,
        limitations=limitations,
        warnings=warnings,
        is_demo=is_demo,
    )
    now = datetime.now(UTC)
    run = ReportRun(
        id=run_id,
        report_type=payload.report_type,
        title=payload.title,
        status="completed",
        report_cutoff=payload.report_cutoff,
        created_at=now,
        available_at=now,
        calculation_version=REPORT_VERSION,
        is_demo=is_demo,
        dataset_id=dataset_id,
        forecast_run_id=payload.forecast_run_id,
        scenario_run_id=payload.scenario_run_id,
        scor_assessment_id=payload.scor_assessment_id,
        portfolio_run_id=payload.portfolio_run_id,
        decision_run_id=payload.decision_run_id,
        explanation_run_id=payload.explanation_run_id,
        source_snapshot=sources,
        report_payload={
            "executive_summary": build_executive_summary(sources),
            "coverage": coverage,
            "scope": _scope(sources),
            "section_count": len(sections),
            "snapshot_immutable": True,
            "sources_recalculated": False,
        },
        warnings=warnings,
        limitations=limitations,
    )
    for item in sections:
        run.sections.append(
            ReportSection(
                section_type=str(item["section_type"]),
                position=int(item["position"]),
                payload=item["payload"],
                source_references=item["source_references"],
                completeness=str(item["completeness"]),
            )
        )
    db.add(run)
    db.commit()
    return require_run(db, run.id)


def create_run(db: Session, payload: ReportRequest) -> ReportRun:
    prepared = _prepare(db, payload)
    return _persist(
        db,
        run_id=str(uuid4()),
        payload=payload,
        sources=prepared["sources"],
        coverage=prepared["coverage"],
        limitations=prepared["limitations"],
        warnings=prepared["warnings"],
        dataset_id=prepared["dataset_id"],
    )


def regenerate_demo(db: Session) -> ReportRun:
    existing = db.get(ReportRun, DEMO_REPORT_ID)
    if existing:
        db.delete(existing)
        db.flush()
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    sources: dict[str, object] = {
        "dataset": {"id": "demo", "name": "NEXORA Reporting Demo", "status": "demo"},
        "forecast": {
            "id": "demo-forecast",
            "selection": {"product": "NX-101", "location": "Lima Centro", "category": "Bebidas"},
            "frequency": "weekly",
            "horizon": 4,
            "champion_model": "moving_average",
            "champion_reason": "Menor WMAPE fuera de muestra.",
            "models": [
                {
                    "model_name": "moving_average",
                    "rank": 1,
                    "metrics": {"wmape": 0.1322},
                    "folds": [],
                }
            ],
            "forecast_points": [
                {
                    "timestamp": f"2026-01-{day:02d}",
                    "forecast": value,
                    "lower_80": value - 20,
                    "upper_80": value + 20,
                }
                for day, value in [(5, 276.75), (12, 276.75), (19, 276.75), (26, 276.75)]
            ],
            "warnings": [],
            "recalculated": False,
        },
        "scenario": {
            "id": "demo-scenario",
            "name": "Escenario operativo DEMO",
            "summary": {"relative_delta": -0.054},
            "points": [],
        },
        "scor": {
            "id": "demo-scor",
            "name": "Diagnóstico SCOR DEMO",
            "summary": {"metrics_total": 26, "metrics_complete": 22},
            "criticality": {"critical_processes": ["DELIVER"]},
            "metrics": [],
            "processes": [],
        },
        "portfolio": {
            "id": "demo-portfolio",
            "number_of_series": 6,
            "summary": {"series_evaluated": 6},
            "items": [],
        },
        "decision": {
            "id": "demo-decision",
            "recommendations": [
                {
                    "rank": 1,
                    "priority": "high",
                    "title": "Revisar desempeño de distribución",
                    "support_score": 0.82,
                    "status": "open",
                }
            ],
            "warnings": [],
        },
        "explanation": {
            "id": "demo-explanation",
            "champion_model": "moving_average",
            "version": "demo",
        },
    }
    payload = ReportRequest(
        report_type="integrated",
        title="DEMO · Reporte ejecutivo integrado NEXORA",
        report_cutoff=cutoff,
    )
    coverage = _coverage(sources)
    return _persist(
        db,
        run_id=DEMO_REPORT_ID,
        payload=payload,
        sources=sources,
        coverage=coverage,
        limitations=_limitations(sources),
        warnings=["demo_report_uses_synthetic_decoupled_snapshot"],
        dataset_id=None,
        is_demo=True,
    )


def _query(db: Session):
    return db.query(ReportRun).options(selectinload(ReportRun.sections))


def require_run(db: Session, run_id: str) -> ReportRun:
    run = _query(db).filter(ReportRun.id == run_id).one_or_none()
    if run is None:
        raise DataStudioError("report_run_not_found", "El Report Run no existe.", 404)
    return run


def serialize_section(item: ReportSection) -> dict[str, object]:
    return {
        "id": item.id,
        "section_type": item.section_type,
        "position": item.position,
        "payload": item.payload,
        "source_references": item.source_references,
        "completeness": item.completeness,
        "created_at": item.created_at,
    }


def serialize_run(run: ReportRun, *, details: bool = True) -> dict[str, object]:
    coverage = run.report_payload.get("coverage", {})
    scope = run.report_payload.get("scope", {})
    response = {
        "id": run.id,
        "report_type": run.report_type,
        "title": run.title,
        "status": run.status,
        "report_cutoff": run.report_cutoff,
        "created_at": run.created_at,
        "calculation_version": run.calculation_version,
        "is_demo": run.is_demo,
        "dataset_id": run.dataset_id,
        "forecast_run_id": run.forecast_run_id,
        "scenario_run_id": run.scenario_run_id,
        "scor_assessment_id": run.scor_assessment_id,
        "portfolio_run_id": run.portfolio_run_id,
        "decision_run_id": run.decision_run_id,
        "explanation_run_id": run.explanation_run_id,
        "layer_count": coverage.get("included", 0),
        "coverage": coverage,
        "warning_count": len(run.warnings),
        "scope": scope,
    }
    if details:
        response.update(
            {
                "available_at": run.available_at,
                "source_snapshot": run.source_snapshot,
                "report_payload": run.report_payload,
                "warnings": run.warnings,
                "limitations": run.limitations,
                "sections": [
                    serialize_section(item)
                    for item in sorted(run.sections, key=lambda section: section.position)
                ],
            }
        )
    return response


def list_runs(db: Session) -> list[dict[str, object]]:
    runs = _query(db).order_by(ReportRun.created_at.desc(), ReportRun.id).limit(100).all()
    return [serialize_run(run, details=False) for run in runs]
