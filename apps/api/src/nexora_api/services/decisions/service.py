"""Orchestrate decision preflight, generation, persistence, and lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.decision import (
    DecisionAudit,
    DecisionEvidence,
    DecisionRecommendation,
    DecisionRun,
)
from nexora_api.models.scenario import ScenarioRun
from nexora_api.services.decisions.evidence import collect_evidence
from nexora_api.services.decisions.ranking import rank_candidates

STATUS_TRANSITIONS = {
    "open": {"acknowledged", "under_review", "dismissed", "resolved"},
    "acknowledged": {"under_review", "dismissed", "resolved"},
    "under_review": {"acknowledged", "dismissed", "resolved"},
    "dismissed": {"under_review"},
    "resolved": {"under_review"},
}


def _source_snapshot(evidence: dict[str, object]) -> dict[str, object]:
    return {
        "selection": evidence["selection"],
        "champion": evidence["champion"],
        "forecast_summary": evidence["forecast_summary"],
        "signals": evidence["signals"],
        "impacts": evidence["impacts"],
        "analogies": evidence["analogies"],
        "scenario": evidence["scenario_snapshot"],
        "missing_operational_inputs": evidence["missing_operational_inputs"],
        "scor": evidence["scor_snapshot"],
        "immutable_sources": True,
        "causal_inference": False,
    }


def preflight(
    db: Session,
    forecast_run_id: str,
    scenario_run_id: str | None,
    decision_cutoff: datetime | None,
    scor_assessment_id: str | None = None,
) -> dict[str, object]:
    evidence = collect_evidence(
        db, forecast_run_id, scenario_run_id, decision_cutoff, scor_assessment_id
    )
    forecast = evidence["forecast"]
    cutoff = evidence["decision_cutoff"]
    assert isinstance(cutoff, datetime)
    scenarios = (
        db.query(ScenarioRun)
        .filter(
            ScenarioRun.forecast_run_id == forecast_run_id,
            ScenarioRun.status == "completed",
            ScenarioRun.created_at <= cutoff,
        )
        .order_by(ScenarioRun.created_at.desc(), ScenarioRun.id)
        .all()
    )
    return {
        "forecast_run_id": forecast_run_id,
        "dataset_id": forecast.dataset_id,
        "selection": evidence["selection"],
        "champion": evidence["champion"],
        "forecast_summary": evidence["forecast_summary"],
        "decision_cutoff": cutoff,
        "scenarios": [
            {
                "id": item.id,
                "name": item.name,
                "relative_delta": item.summary_json.get("relative_delta"),
                "affected_periods": item.summary_json.get("affected_periods", 0),
                "warnings": item.warnings,
                "created_at": item.created_at.isoformat(),
                "hypothetical": True,
            }
            for item in scenarios
        ],
        "relevant_context": evidence["signals"],
        "usable_impacts": list(evidence["impacts"].values()),
        "missing_operational_inputs": evidence["missing_operational_inputs"],
        "scor_assessments": evidence["scor_assessments"],
        "selected_scor": evidence["scor_snapshot"],
        "warnings": [
            "recommendations_are_not_orders",
            "official_forecast_remains_unchanged",
            "context_association_is_not_causality",
        ],
    }


def generate_decision_run(
    db: Session,
    forecast_run_id: str,
    scenario_run_id: str | None,
    decision_cutoff: datetime | None,
    scor_assessment_id: str | None = None,
) -> DecisionRun:
    from nexora_api.services.decisions.rules import generate_candidates

    evidence = collect_evidence(
        db, forecast_run_id, scenario_run_id, decision_cutoff, scor_assessment_id
    )
    forecast = evidence["forecast"]
    cutoff = evidence["decision_cutoff"]
    assert isinstance(cutoff, datetime)
    candidates = rank_candidates(generate_candidates(evidence))
    run = DecisionRun(
        id=str(uuid4()),
        forecast_run_id=forecast_run_id,
        scenario_run_id=scenario_run_id,
        dataset_id=forecast.dataset_id,
        decision_cutoff=cutoff,
        source_snapshot=_source_snapshot(evidence),
        warnings=[
            "recommendations_are_not_orders",
            "official_forecast_remains_unchanged",
            "context_association_is_not_causality",
        ],
    )
    db.add(run)
    db.flush()
    priority_counts = {priority: 0 for priority in ("low", "medium", "high", "critical")}
    for rank, candidate in enumerate(candidates, start=1):
        priority = str(candidate["priority"])
        priority_counts[priority] += 1
        recommendation = DecisionRecommendation(
            id=str(uuid4()),
            decision_run_id=run.id,
            rank=rank,
            priority=priority,
            action_type=str(candidate["action_type"]),
            title=str(candidate["title"]),
            summary=str(candidate["summary"]),
            rationale=str(candidate["rationale"]),
            support_score=float(candidate["support_score"]),
            evidence_level=str(candidate["evidence_level"]),
            scope_json=evidence["selection"],
            dataset_id=forecast.dataset_id,
            product=forecast.product,
            location=forecast.location,
            category=forecast.category,
            forecast_run_id=forecast_run_id,
            scenario_run_id=scenario_run_id,
            context_signal_ids=list(candidate["context_signal_ids"]),
            context_impact_ids=list(candidate["context_impact_ids"]),
            decision_cutoff=cutoff,
            limitations=list(candidate["limitations"]),
            provenance_json={
                **candidate["provenance"],
                "stable_key": candidate["stable_key"],
                "decision_cutoff": cutoff.isoformat(),
                "forecast_run_id": forecast_run_id,
                "scenario_run_id": scenario_run_id,
                "scor_assessment_id": candidate["provenance"].get(
                    "scor_assessment_id"
                ),
            },
        )
        db.add(recommendation)
        db.flush()
        for item in candidate["evidence"]:
            db.add(
                DecisionEvidence(
                    recommendation_id=recommendation.id,
                    evidence_type=str(item["evidence_type"]),
                    source_id=item.get("source_id"),
                    description=str(item["description"]),
                    snapshot_json=item["snapshot"],
                )
            )
        db.add(
            DecisionAudit(
                recommendation_id=recommendation.id,
                action="created",
                from_status=None,
                to_status="open",
                details={
                    "rank": rank,
                    "rule_version": "decision_rules_v1",
                    "scor_rule_version": candidate["provenance"].get(
                        "scor_rule_version",
                        candidate["provenance"].get("rule_version")
                        if candidate["provenance"].get("scor_origin")
                        else None,
                    ),
                    "scor_assessment_id": candidate["provenance"].get(
                        "scor_assessment_id"
                    ),
                    "scor_support_contribution": candidate["provenance"].get(
                        "scor_support_contribution", 0
                    ),
                    "automatic_execution": False,
                },
            )
        )
    run.summary_json = {
        "recommendation_count": len(candidates),
        "priority_counts": priority_counts,
        "high_priority_count": priority_counts["high"] + priority_counts["critical"],
        "requires_review_count": sum(
            item["action_type"] == "manual_review_required" for item in candidates
        ),
        "scenario_considered": scenario_run_id is not None,
        "context_signal_count": len(evidence["signals"]),
        "context_impact_count": len(evidence["impacts"]),
        "scor_assessments_considered": 1 if evidence["scor_snapshot"] else 0,
        "scor_recommendation_count": sum(
            bool(item["provenance"].get("scor_origin")) for item in candidates
        ),
    }
    db.commit()
    return require_run(db, run.id)


def _run_query(db: Session):
    return db.query(DecisionRun).options(
        selectinload(DecisionRun.recommendations).selectinload(DecisionRecommendation.evidence),
        selectinload(DecisionRun.recommendations).selectinload(
            DecisionRecommendation.audit_entries
        ),
    )


def require_run(db: Session, run_id: str) -> DecisionRun:
    run = _run_query(db).filter(DecisionRun.id == run_id).one_or_none()
    if run is None:
        raise DataStudioError("decision_run_not_found", "El análisis de decisión no existe.", 404)
    return run


def require_recommendation(db: Session, recommendation_id: str) -> DecisionRecommendation:
    recommendation = (
        db.query(DecisionRecommendation)
        .options(
            selectinload(DecisionRecommendation.evidence),
            selectinload(DecisionRecommendation.audit_entries),
        )
        .filter(DecisionRecommendation.id == recommendation_id)
        .one_or_none()
    )
    if recommendation is None:
        raise DataStudioError(
            "decision_recommendation_not_found", "La recomendación no existe.", 404
        )
    return recommendation


def change_status(
    db: Session, recommendation_id: str, status: str, note: str | None
) -> DecisionRecommendation:
    recommendation = require_recommendation(db, recommendation_id)
    current = recommendation.status
    if status == current:
        return recommendation
    if status not in STATUS_TRANSITIONS.get(current, set()):
        raise DataStudioError(
            "invalid_decision_status_transition",
            f"No se permite cambiar una recomendación de {current} a {status}.",
            409,
        )
    recommendation.status = status
    recommendation.updated_at = datetime.now(UTC)
    recommendation.audit_entries.append(
        DecisionAudit(
            action="status_changed",
            from_status=current,
            to_status=status,
            details={"note": note} if note else {},
        )
    )
    db.commit()
    return require_recommendation(db, recommendation_id)


def serialize_evidence(item: DecisionEvidence) -> dict[str, object]:
    return {
        "id": item.id,
        "evidence_type": item.evidence_type,
        "source_id": item.source_id,
        "description": item.description,
        "snapshot": item.snapshot_json,
        "created_at": item.created_at,
    }


def serialize_recommendation(item: DecisionRecommendation) -> dict[str, object]:
    audit = sorted(item.audit_entries, key=lambda entry: (entry.created_at, entry.id))
    return {
        "id": item.id,
        "decision_run_id": item.decision_run_id,
        "rank": item.rank,
        "priority": item.priority,
        "action_type": item.action_type,
        "title": item.title,
        "summary": item.summary,
        "rationale": item.rationale,
        "support_score": item.support_score,
        "evidence_level": item.evidence_level,
        "scope": item.scope_json,
        "dataset_id": item.dataset_id,
        "product": item.product,
        "location": item.location,
        "category": item.category,
        "forecast_run_id": item.forecast_run_id,
        "scenario_run_id": item.scenario_run_id,
        "context_signal_ids": item.context_signal_ids,
        "context_impact_ids": item.context_impact_ids,
        "scor_assessment_id": item.provenance_json.get("scor_assessment_id"),
        "scor_support_contribution": item.provenance_json.get("scor_support_contribution", 0),
        "scor_origin": item.provenance_json.get("scor_origin"),
        "decision_cutoff": item.decision_cutoff,
        "status": item.status,
        "limitations": item.limitations,
        "provenance": item.provenance_json,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "evidence": [
            serialize_evidence(entry) for entry in sorted(item.evidence, key=lambda entry: entry.id)
        ],
        "audit": [
            {
                "id": entry.id,
                "action": entry.action,
                "from_status": entry.from_status,
                "to_status": entry.to_status,
                "details": entry.details,
                "created_at": entry.created_at,
            }
            for entry in audit
        ],
    }


def serialize_run(run: DecisionRun, *, details: bool = True) -> dict[str, object]:
    recommendations = sorted(run.recommendations, key=lambda item: item.rank)
    return {
        "id": run.id,
        "forecast_run_id": run.forecast_run_id,
        "scenario_run_id": run.scenario_run_id,
        "scor_assessment_id": (
            run.source_snapshot.get("scor", {}).get("scor_assessment_id")
            if isinstance(run.source_snapshot.get("scor"), dict)
            else None
        ),
        "dataset_id": run.dataset_id,
        "decision_cutoff": run.decision_cutoff,
        "status": run.status,
        "source_snapshot": run.source_snapshot,
        "summary": run.summary_json,
        "warnings": run.warnings,
        "recommendation_count": len(recommendations),
        "high_priority_count": run.summary_json.get("high_priority_count", 0),
        "created_at": run.created_at,
        "recommendations": (
            [serialize_recommendation(item) for item in recommendations] if details else []
        ),
    }


def list_runs(db: Session) -> list[dict[str, object]]:
    runs = _run_query(db).order_by(DecisionRun.created_at.desc()).limit(100).all()
    return [serialize_run(run, details=False) for run in runs]


def comparison(run: DecisionRun) -> dict[str, object]:
    forecast_summary = run.source_snapshot["forecast_summary"]
    scenario = run.source_snapshot.get("scenario")
    baseline_total = float(forecast_summary["total"])
    if not isinstance(scenario, dict):
        return {
            "forecast_run_id": run.forecast_run_id,
            "scenario_run_id": None,
            "baseline_total": baseline_total,
            "scenario_total": None,
            "absolute_delta": None,
            "relative_delta": None,
            "affected_periods": 0,
            "scenario_is_hypothetical": False,
            "official_forecast_modified": False,
        }
    summary = scenario["summary"]
    return {
        "forecast_run_id": run.forecast_run_id,
        "scenario_run_id": run.scenario_run_id,
        "baseline_total": baseline_total,
        "scenario_total": summary.get("scenario_total"),
        "absolute_delta": summary.get("absolute_delta"),
        "relative_delta": summary.get("relative_delta"),
        "affected_periods": summary.get("affected_periods", 0),
        "scenario_is_hypothetical": True,
        "official_forecast_modified": False,
    }
