"""Prepare immutable, temporally safe SCOR evidence for Decision Engine."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import ForecastRun
from nexora_api.models.scor import (
    ScorAssessmentRun,
    ScorBenchmarkProfile,
    ScorMetricInput,
    ScorMetricResult,
    ScorProcessResult,
)
from nexora_api.services.scor.definitions import BY_ID


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _assessment_query(db: Session):
    return db.query(ScorAssessmentRun).options(
        selectinload(ScorAssessmentRun.metric_inputs),
        selectinload(ScorAssessmentRun.metric_results),
        selectinload(ScorAssessmentRun.process_results),
        selectinload(ScorAssessmentRun.audit_entries),
    )


def _available_at(assessment: ScorAssessmentRun) -> datetime | None:
    if assessment.calculated_at is None:
        return None
    return max(_utc(assessment.created_at), _utc(assessment.calculated_at))


def _compatibility(assessment: ScorAssessmentRun, forecast: ForecastRun) -> tuple[bool, str]:
    if assessment.source_dataset_id:
        return (
            assessment.source_dataset_id == forecast.dataset_id,
            "dataset_id_exact_match",
        )
    if assessment.forecast_run_id:
        return (
            assessment.forecast_run_id == forecast.id,
            "forecast_run_exact_match",
        )
    if assessment.source_metadata.get("scope_type") == "entity":
        return True, "declared_entity_scope"
    # v0.8.0 persisted the deterministic product demo before ``scope_type``
    # was part of its metadata contract. Its fixed seed is a safe, explicit
    # compatibility marker; arbitrary unscoped assessments remain excluded.
    if assessment.source_metadata.get("demo_seed") == 6001:
        return True, "legacy_demo_entity_scope"
    return False, "dataset_or_entity_scope_missing"


def _is_temporally_available(
    assessment: ScorAssessmentRun, decision_cutoff: datetime
) -> tuple[bool, str]:
    available_at = _available_at(assessment)
    if assessment.status != "calculated" or available_at is None:
        return False, "assessment_not_calculated"
    if _utc(assessment.cutoff) > decision_cutoff:
        return False, "assessment_knowledge_after_decision_cutoff"
    if available_at > decision_cutoff:
        return False, "assessment_available_after_decision_cutoff"
    if _utc(assessment.period_end) > decision_cutoff:
        return False, "assessment_period_after_decision_cutoff"
    return True, "available"


def _profile(db: Session, profile_id: str | None) -> ScorBenchmarkProfile | None:
    if not profile_id:
        return None
    return (
        db.query(ScorBenchmarkProfile).filter(ScorBenchmarkProfile.id == profile_id).one_or_none()
    )


def list_available_scor_assessments(
    db: Session, forecast: ForecastRun, decision_cutoff: datetime
) -> list[dict[str, object]]:
    cutoff = _utc(decision_cutoff)
    assessments = (
        _assessment_query(db)
        .filter(ScorAssessmentRun.status == "calculated")
        .order_by(ScorAssessmentRun.calculated_at.desc(), ScorAssessmentRun.id)
        .all()
    )
    output: list[dict[str, object]] = []
    for assessment in assessments:
        compatible, compatibility_reason = _compatibility(assessment, forecast)
        temporal, temporal_reason = _is_temporally_available(assessment, cutoff)
        if not compatible or not temporal:
            continue
        profile = _profile(db, assessment.benchmark_profile_id)
        output.append(
            {
                "id": assessment.id,
                "name": assessment.name,
                "company_name": assessment.company_name,
                "period_start": assessment.period_start.isoformat(),
                "period_end": assessment.period_end.isoformat(),
                "cutoff": assessment.cutoff.isoformat(),
                "calculated_at": assessment.calculated_at.isoformat(),
                "available_at": _available_at(assessment).isoformat(),
                "benchmark_profile_id": assessment.benchmark_profile_id,
                "benchmark_profile_name": profile.name if profile else None,
                "metrics_complete": assessment.summary_json.get("metrics_complete", 0),
                "metrics_insufficient": assessment.summary_json.get("metrics_insufficient", 0),
                "metrics_incomplete": assessment.summary_json.get("metrics_incomplete", 0),
                "metrics_not_applicable": assessment.summary_json.get("metrics_not_applicable", 0),
                "data_coverage": assessment.summary_json.get("data_coverage", 0),
                "benchmark_coverage": assessment.summary_json.get("benchmark_coverage", 0),
                "criticality_status": assessment.criticality_json.get(
                    "status", "insufficient_evidence"
                ),
                "selected_process": assessment.criticality_json.get("selected_process"),
                "tied_processes": assessment.criticality_json.get("tied_processes", []),
                "compatibility_reason": compatibility_reason,
                "temporal_reason": temporal_reason,
            }
        )
    return output


def _input_snapshot(item: ScorMetricInput | None) -> dict[str, object]:
    if item is None:
        return {}
    return {
        "source": item.source,
        "available_at": item.available_at.isoformat(),
        "provenance": item.provenance_json,
        "metadata": item.metadata_json,
        "not_applicable": item.not_applicable,
    }


def _process_snapshot(item: ScorProcessResult) -> dict[str, object]:
    return {
        "process": item.process,
        "metrics_total": item.metrics_total,
        "metrics_evaluable": item.metrics_evaluable,
        "data_coverage": item.data_coverage,
        "benchmark_coverage": item.benchmark_coverage,
        "weighted_gap_score": item.weighted_gap_score,
        "confidence": item.confidence,
        "rank": item.rank,
        "contributors": item.details_json.get("contributors", []),
    }


def _metric_snapshot(
    item: ScorMetricResult,
    input_item: ScorMetricInput | None,
    process: ScorProcessResult | None,
    cutoff: datetime,
) -> tuple[dict[str, object], bool]:
    input_available = input_item is None or _utc(input_item.available_at) <= cutoff
    snapshot = {
        "metric_id": item.metric_id,
        "process": item.process,
        "attribute": item.attribute,
        "metric_name": BY_ID[item.metric_id].display_name,
        "raw_result": item.result_value if input_available else None,
        "unit": item.unit,
        "target": item.target_snapshot,
        "gap_score": item.gap_score if input_available else None,
        "evidence_status": item.evidence_status if input_available else "excluded_after_cutoff",
        "reason": item.reason if input_available else "metric_available_after_decision_cutoff",
        "process_coverage": process.benchmark_coverage if process else 0,
        "process_data_coverage": process.data_coverage if process else 0,
        "calculated_at": item.calculated_at.isoformat(),
        "calculation_version": item.algorithm_version,
        "input_provenance": _input_snapshot(input_item),
        "temporally_available": input_available,
    }
    return snapshot, input_available


def prepare_scor_evidence(
    db: Session,
    forecast: ForecastRun,
    assessment_id: str,
    decision_cutoff: datetime,
) -> dict[str, object]:
    cutoff = _utc(decision_cutoff)
    assessment = _assessment_query(db).filter(ScorAssessmentRun.id == assessment_id).one_or_none()
    if assessment is None:
        raise DataStudioError(
            "decision_scor_not_found", "El diagnóstico SCOR seleccionado no existe.", 404
        )
    compatible, compatibility_reason = _compatibility(assessment, forecast)
    if not compatible:
        raise DataStudioError(
            "decision_scor_incompatible",
            "El diagnóstico SCOR no pertenece al dataset, Forecast Run o entidad compatible.",
            409,
        )
    available, availability_reason = _is_temporally_available(assessment, cutoff)
    if not available:
        raise DataStudioError(
            "decision_scor_after_cutoff",
            f"El diagnóstico SCOR no estaba disponible al corte: {availability_reason}.",
            409,
        )
    profile = _profile(db, assessment.benchmark_profile_id)
    inputs = {item.metric_id: item for item in assessment.metric_inputs}
    processes = {item.process: item for item in assessment.process_results}
    metrics: list[dict[str, object]] = []
    excluded: list[str] = []
    for result in sorted(assessment.metric_results, key=lambda item: item.metric_id):
        snapshot, input_available = _metric_snapshot(
            result, inputs.get(result.metric_id), processes.get(result.process), cutoff
        )
        metrics.append(snapshot)
        if not input_available:
            excluded.append(result.metric_id)
    return {
        "scor_assessment_id": assessment.id,
        "assessment_name": assessment.name,
        "entity": assessment.company_name,
        "source_dataset_id": assessment.source_dataset_id,
        "forecast_run_id": assessment.forecast_run_id,
        "period_start": assessment.period_start.isoformat(),
        "period_end": assessment.period_end.isoformat(),
        "assessment_cutoff": assessment.cutoff.isoformat(),
        "calculated_at": assessment.calculated_at.isoformat(),
        "available_at": _available_at(assessment).isoformat(),
        "benchmark_profile_id": assessment.benchmark_profile_id,
        "benchmark_profile_name": profile.name if profile else None,
        "benchmark_profile_source": profile.source if profile else None,
        "summary": assessment.summary_json,
        "criticality": assessment.criticality_json,
        "processes": [
            _process_snapshot(item)
            for item in sorted(assessment.process_results, key=lambda item: item.process)
        ],
        "metrics": metrics,
        "excluded_metric_ids": excluded,
        "calculation_version": assessment.algorithm_version,
        "provenance": {
            "source_name": assessment.source_name,
            "source_metadata": assessment.source_metadata,
            "compatibility_reason": compatibility_reason,
            "availability_rule": "available_at <= decision_cutoff",
            "assessment_snapshot_immutable": True,
            "official_scor_score": False,
        },
        "decision_cutoff": cutoff.isoformat(),
    }
