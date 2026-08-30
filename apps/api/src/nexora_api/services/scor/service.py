"""SCOR assessment orchestration, persistence, and serialization."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import ForecastRun
from nexora_api.models.scor import (
    ScorAssessmentRun,
    ScorAudit,
    ScorBenchmarkProfile,
    ScorBenchmarkTarget,
    ScorMetricInput,
    ScorMetricResult,
    ScorProcessResult,
)
from nexora_api.schemas.scor import ScorAssessmentCreate, ScorBenchmarkProfileCreate
from nexora_api.services.scor.benchmarking import gap_score
from nexora_api.services.scor.calculator import Calculation, calculate_metric
from nexora_api.services.scor.criticality import determine_critical_process, process_scores
from nexora_api.services.scor.definitions import BY_ID, ENGINE_VERSION, METRICS
from nexora_api.services.scor.validation import validate_period


def _error(code: str, message: str, status: int = 422) -> DataStudioError:
    return DataStudioError(code, message, status)


def _validate_forecast_association(db: Session, payload: ScorAssessmentCreate) -> None:
    if not payload.forecast_run_id:
        return
    run = db.query(ForecastRun).filter(ForecastRun.id == payload.forecast_run_id).one_or_none()
    if run is None or run.status != "completed":
        raise _error(
            "scor_forecast_unavailable", "El Forecast Run asociado no está completado.", 409
        )
    if payload.source_dataset_id and run.dataset_id != payload.source_dataset_id:
        raise _error(
            "scor_forecast_incompatible", "El Forecast Run pertenece a otro conjunto de datos.", 409
        )
    if run.data_cutoff >= payload.period_start:
        raise _error(
            "scor_forecast_temporal_leakage",
            "El forecast debe haberse originado antes del periodo evaluado.",
            409,
        )
    if run.created_at > payload.cutoff:
        raise _error(
            "scor_forecast_temporal_leakage", "El Forecast Run no estaba disponible al corte.", 409
        )
    points = sorted(run.points, key=lambda item: item.timestamp)
    if (
        not points
        or points[0].timestamp > payload.period_start
        or points[-1].timestamp < payload.period_end
    ):
        raise _error(
            "scor_forecast_incompatible_period",
            "El Forecast Run no cubre el periodo completo del KPI P01.",
            409,
        )


def create_assessment(
    db: Session, payload: ScorAssessmentCreate, *, assessment_id: str | None = None
) -> ScorAssessmentRun:
    try:
        validate_period(payload.period_start, payload.period_end, payload.cutoff)
    except ValueError as error:
        raise _error("invalid_scor_period", str(error)) from error
    _validate_forecast_association(db, payload)
    metric_ids = [item.metric_id for item in payload.metric_inputs]
    if len(metric_ids) != len(set(metric_ids)):
        raise _error("duplicate_scor_metric", "Cada KPI solo puede registrarse una vez.")
    if unknown := sorted(set(metric_ids) - set(BY_ID)):
        raise _error("unknown_scor_metric", f"KPI no reconocido: {', '.join(unknown)}")
    for item in payload.metric_inputs:
        if item.available_at > payload.cutoff:
            raise _error(
                "scor_temporal_leakage_blocked",
                f"{item.metric_id} no estaba disponible al corte.",
                409,
            )
    run = ScorAssessmentRun(
        id=assessment_id or str(uuid4()),
        name=payload.name,
        company_name=payload.company_name,
        source_dataset_id=payload.source_dataset_id,
        forecast_run_id=payload.forecast_run_id,
        benchmark_profile_id=payload.benchmark_profile_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        cutoff=payload.cutoff,
        source_name=payload.source_name,
        source_metadata=payload.source_metadata,
        algorithm_version=ENGINE_VERSION,
    )
    db.add(run)
    db.flush()
    for item in payload.metric_inputs:
        run.metric_inputs.append(
            ScorMetricInput(
                metric_id=item.metric_id,
                values_json=item.values,
                monthly_values_json=item.monthly_values,
                metadata_json=item.metadata,
                source=item.source,
                provenance_json=item.provenance,
                not_applicable=item.not_applicable,
                available_at=item.available_at,
            )
        )
    run.audit_entries.append(
        ScorAudit(
            action="created",
            details_json={
                "metric_inputs": len(payload.metric_inputs),
                "cutoff": payload.cutoff.isoformat(),
                "algorithm_version": ENGINE_VERSION,
            },
        )
    )
    db.commit()
    return require_assessment(db, run.id)


def calculate_assessment(db: Session, assessment_id: str) -> ScorAssessmentRun:
    run = require_assessment(db, assessment_id)
    input_by_metric = {item.metric_id: item for item in run.metric_inputs}
    calculations: dict[str, Calculation] = {}
    for definition in METRICS:
        item = input_by_metric.get(definition.id)
        calculations[definition.id] = calculate_metric(
            definition.id,
            item.values_json if item else {},
            monthly_values=item.monthly_values_json if item else [],
            metadata=item.metadata_json if item else {},
            dependencies=calculations,
            not_applicable=item.not_applicable if item else False,
        )
    run.metric_results.clear()
    run.process_results.clear()
    db.flush()
    target_map = _target_map(db, run.benchmark_profile_id)
    metric_snapshots: list[dict[str, object]] = []
    for definition in METRICS:
        calculation = calculations[definition.id]
        target = target_map.get(definition.id)
        target_snapshot: dict[str, object] = {}
        score = None
        if target and calculation.evidence_status == "complete" and calculation.result is not None:
            evaluation = gap_score(
                calculation.result,
                direction=target.direction,
                target=target.target,
                minimum=target.optional_min,
                maximum=target.optional_max,
            )
            target_snapshot = _serialize_target(target) | {
                "evaluation_status": evaluation.status,
                "explanation": evaluation.explanation,
            }
            score = evaluation.score
        result = ScorMetricResult(
            metric_id=definition.id,
            process=definition.process,
            attribute=definition.attribute,
            method=calculation.method,
            formula=calculation.formula,
            substituted_formula=calculation.substituted_formula,
            inputs_snapshot=calculation.inputs,
            numerator=calculation.numerator,
            denominator=calculation.denominator,
            result_value=calculation.result,
            ratio_decimal=calculation.ratio_decimal,
            unit=calculation.unit,
            evidence_status=calculation.evidence_status,
            reason=calculation.reason,
            calculation_details=calculation.details,
            target_snapshot=target_snapshot,
            gap_score=score,
            algorithm_version=ENGINE_VERSION,
        )
        run.metric_results.append(result)
        metric_snapshots.append(
            {
                "metric_id": definition.id,
                "evidence_status": calculation.evidence_status,
                "gap_score": score,
                "target_weight": target.weight if target and score is not None else 0,
            }
        )
    minimum_coverage, profile_id = _profile_context(db, run.benchmark_profile_id)
    process_payloads = process_scores(metric_snapshots, minimum_coverage)
    criticality = determine_critical_process(
        process_payloads, profile_id=profile_id, minimum_coverage=minimum_coverage
    )
    ranked = criticality.get("process_scores", [])
    rank_map = {item["process"]: index for index, item in enumerate(ranked, start=1)}
    for item in process_payloads:
        run.process_results.append(
            ScorProcessResult(
                process=str(item["process"]),
                metrics_total=int(item["metrics_total"]),
                metrics_complete=int(item["metrics_complete"]),
                metrics_insufficient=int(item["metrics_insufficient"]),
                metrics_not_applicable=int(item["metrics_not_applicable"]),
                metrics_evaluable=int(item["metrics_evaluable"]),
                data_coverage=float(item["data_coverage"]),
                benchmark_coverage=float(item["benchmark_coverage"]),
                weighted_gap_score=item["weighted_gap_score"],
                confidence=str(item["confidence"]),
                rank=rank_map.get(item["process"]),
                details_json={"contributors": item["contributors"]},
            )
        )
    statuses = [item.evidence_status for item in calculations.values()]
    run.summary_json = {
        "metrics_total": len(METRICS),
        "metrics_complete": statuses.count("complete"),
        "metrics_incomplete": statuses.count("incomplete"),
        "metrics_insufficient": statuses.count("insufficient_evidence") + statuses.count("invalid"),
        "metrics_not_applicable": statuses.count("not_applicable"),
        "data_coverage": round(statuses.count("complete") / len(METRICS), 4),
        "benchmark_coverage": round(
            sum(item.get("gap_score") is not None for item in metric_snapshots) / len(METRICS), 4
        ),
    }
    run.criticality_json = criticality
    run.warnings = sorted(
        {calculation.reason for calculation in calculations.values() if calculation.reason}
    )
    run.status = "calculated"
    run.calculated_at = datetime.now(UTC)
    run.audit_entries.append(
        ScorAudit(
            action="calculated",
            details_json={
                "summary": run.summary_json,
                "criticality_status": criticality["status"],
                "benchmark_profile_id": run.benchmark_profile_id,
            },
        )
    )
    db.commit()
    return require_assessment(db, run.id)


def apply_benchmark(db: Session, assessment_id: str, profile_id: str) -> ScorAssessmentRun:
    run = require_assessment(db, assessment_id)
    profile = require_profile(db, profile_id)
    if not profile.active:
        raise _error("scor_benchmark_inactive", "El perfil de metas no está activo.", 409)
    run.benchmark_profile_id = profile.id
    run.audit_entries.append(
        ScorAudit(action="benchmark_selected", details_json={"profile_id": profile.id})
    )
    db.commit()
    return calculate_assessment(db, assessment_id)


def create_profile(
    db: Session, payload: ScorBenchmarkProfileCreate, *, profile_id: str | None = None
) -> ScorBenchmarkProfile:
    metric_ids = [item.metric_id for item in payload.targets]
    if len(metric_ids) != len(set(metric_ids)) or set(metric_ids) - set(BY_ID):
        raise _error("invalid_scor_benchmark_metrics", "Targets duplicados o KPI desconocidos.")
    profile = ScorBenchmarkProfile(
        id=profile_id or str(uuid4()),
        name=payload.name,
        profile_type=payload.profile_type,
        active=payload.active,
        source=payload.source,
        notes=payload.notes,
        is_official_scor=False,
        minimum_process_coverage=payload.minimum_process_coverage,
    )
    db.add(profile)
    for item in payload.targets:
        evaluation = gap_score(
            0,
            direction=item.direction,
            target=item.target,
            minimum=item.optional_min,
            maximum=item.optional_max,
        )
        if evaluation.status == "invalid_target":
            raise _error(
                "invalid_scor_benchmark_target", f"{item.metric_id}: {evaluation.explanation}"
            )
        profile.targets.append(
            ScorBenchmarkTarget(
                metric_id=item.metric_id,
                direction=item.direction,
                target=item.target,
                optional_min=item.optional_min,
                optional_max=item.optional_max,
                weight=item.weight,
                source=item.source,
                notes=item.notes,
            )
        )
    db.commit()
    return require_profile(db, profile.id)


def _assessment_query(db: Session):
    return db.query(ScorAssessmentRun).options(
        selectinload(ScorAssessmentRun.metric_inputs),
        selectinload(ScorAssessmentRun.metric_results),
        selectinload(ScorAssessmentRun.process_results),
        selectinload(ScorAssessmentRun.audit_entries),
    )


def require_assessment(db: Session, assessment_id: str) -> ScorAssessmentRun:
    run = _assessment_query(db).filter(ScorAssessmentRun.id == assessment_id).one_or_none()
    if run is None:
        raise _error("scor_assessment_not_found", "El diagnóstico SCOR no existe.", 404)
    return run


def require_profile(db: Session, profile_id: str) -> ScorBenchmarkProfile:
    profile = (
        db.query(ScorBenchmarkProfile)
        .options(selectinload(ScorBenchmarkProfile.targets))
        .filter(ScorBenchmarkProfile.id == profile_id)
        .one_or_none()
    )
    if profile is None:
        raise _error("scor_benchmark_not_found", "El perfil de metas no existe.", 404)
    return profile


def list_assessments(db: Session) -> list[dict[str, object]]:
    return [
        serialize_assessment_summary(item)
        for item in _assessment_query(db).order_by(ScorAssessmentRun.created_at.desc()).all()
    ]


def list_profiles(db: Session) -> list[dict[str, object]]:
    profiles = (
        db.query(ScorBenchmarkProfile)
        .options(selectinload(ScorBenchmarkProfile.targets))
        .order_by(ScorBenchmarkProfile.created_at.desc())
        .all()
    )
    return [serialize_profile(item) for item in profiles]


def _target_map(db: Session, profile_id: str | None) -> dict[str, ScorBenchmarkTarget]:
    if not profile_id:
        return {}
    return {item.metric_id: item for item in require_profile(db, profile_id).targets}


def _profile_context(db: Session, profile_id: str | None) -> tuple[float, str | None]:
    if not profile_id:
        return 0.5, None
    profile = require_profile(db, profile_id)
    return profile.minimum_process_coverage, profile.id


def _serialize_target(item: ScorBenchmarkTarget) -> dict[str, object]:
    return {
        "metric_id": item.metric_id,
        "direction": item.direction,
        "target": item.target,
        "optional_min": item.optional_min,
        "optional_max": item.optional_max,
        "weight": item.weight,
        "source": item.source,
        "notes": item.notes,
    }


def serialize_profile(item: ScorBenchmarkProfile) -> dict[str, object]:
    return {
        "id": item.id,
        "name": item.name,
        "profile_type": item.profile_type,
        "active": item.active,
        "source": item.source,
        "notes": item.notes,
        "is_official_scor": item.is_official_scor,
        "minimum_process_coverage": item.minimum_process_coverage,
        "targets": [
            _serialize_target(target)
            for target in sorted(item.targets, key=lambda target: target.metric_id)
        ],
        "created_at": item.created_at,
    }


def serialize_metric_input(item: ScorMetricInput) -> dict[str, object]:
    return {
        "id": item.id,
        "metric_id": item.metric_id,
        "values": item.values_json,
        "monthly_values": item.monthly_values_json,
        "metadata": item.metadata_json,
        "source": item.source,
        "provenance": item.provenance_json,
        "not_applicable": item.not_applicable,
        "available_at": item.available_at,
        "created_at": item.created_at,
    }


def serialize_metric_result(item: ScorMetricResult) -> dict[str, object]:
    definition = BY_ID[item.metric_id]
    return {
        "id": item.id,
        "metric_id": item.metric_id,
        "process": item.process,
        "process_label": definition.as_dict()["process_label"],
        "attribute": item.attribute,
        "display_name": definition.display_name,
        "method": item.method,
        "formula": item.formula,
        "substituted_formula": item.substituted_formula,
        "inputs": item.inputs_snapshot,
        "numerator": item.numerator,
        "denominator": item.denominator,
        "result_value": item.result_value,
        "ratio_decimal": item.ratio_decimal,
        "unit": item.unit,
        "evidence_status": item.evidence_status,
        "reason": item.reason,
        "calculation_details": item.calculation_details,
        "target": item.target_snapshot,
        "gap_score": item.gap_score,
        "calculated_at": item.calculated_at,
        "algorithm_version": item.algorithm_version,
    }


def serialize_process(item: ScorProcessResult) -> dict[str, object]:
    return {
        "id": item.id,
        "process": item.process,
        "metrics_total": item.metrics_total,
        "metrics_complete": item.metrics_complete,
        "metrics_insufficient": item.metrics_insufficient,
        "metrics_not_applicable": item.metrics_not_applicable,
        "metrics_evaluable": item.metrics_evaluable,
        "data_coverage": item.data_coverage,
        "benchmark_coverage": item.benchmark_coverage,
        "weighted_gap_score": item.weighted_gap_score,
        "confidence": item.confidence,
        "rank": item.rank,
        "details": item.details_json,
    }


def serialize_assessment_summary(run: ScorAssessmentRun) -> dict[str, object]:
    return {
        "id": run.id,
        "name": run.name,
        "company_name": run.company_name,
        "period_start": run.period_start,
        "period_end": run.period_end,
        "cutoff": run.cutoff,
        "status": run.status,
        "source_name": run.source_name,
        "benchmark_profile_id": run.benchmark_profile_id,
        "forecast_run_id": run.forecast_run_id,
        "metric_count": len(run.metric_results),
        "created_at": run.created_at,
        "calculated_at": run.calculated_at,
    }


def serialize_assessment(run: ScorAssessmentRun) -> dict[str, object]:
    return serialize_assessment_summary(run) | {
        "source_dataset_id": run.source_dataset_id,
        "source_metadata": run.source_metadata,
        "summary": run.summary_json,
        "criticality": run.criticality_json,
        "warnings": run.warnings,
        "algorithm_version": run.algorithm_version,
        "metric_inputs": [
            serialize_metric_input(item)
            for item in sorted(run.metric_inputs, key=lambda item: item.metric_id)
        ],
        "metrics": [
            serialize_metric_result(item)
            for item in sorted(run.metric_results, key=lambda item: item.metric_id)
        ],
        "processes": [
            serialize_process(item)
            for item in sorted(run.process_results, key=lambda item: item.process)
        ],
        "audit": [
            {
                "id": item.id,
                "action": item.action,
                "details": item.details_json,
                "created_at": item.created_at,
            }
            for item in sorted(run.audit_entries, key=lambda item: item.id)
        ],
    }
