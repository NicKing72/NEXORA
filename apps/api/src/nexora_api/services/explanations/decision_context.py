"""Optional downstream layers kept separate from mathematical forecast evidence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.decision import DecisionRun
from nexora_api.models.portfolio import PortfolioRun
from nexora_api.models.scenario import ScenarioRun
from nexora_api.models.scor import ScorAssessmentRun


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _not_found(code: str, label: str) -> DataStudioError:
    return DataStudioError(code, f"The requested {label} does not exist.", 404)


def prepare_layers(
    db: Session,
    *,
    forecast_run_id: str,
    dataset_id: str,
    cutoff: datetime,
    scenario_run_id: str | None,
    scor_assessment_id: str | None,
    portfolio_run_id: str | None,
    decision_run_id: str | None,
) -> dict[str, object]:
    """Validate availability and return independent, frozen downstream snapshots."""
    layers: dict[str, object] = {
        "scenario": None,
        "scor": None,
        "portfolio": None,
        "decision": None,
        "context": None,
    }
    if scenario_run_id:
        item = db.query(ScenarioRun).filter(ScenarioRun.id == scenario_run_id).one_or_none()
        if item is None:
            raise _not_found("scenario_not_found", "scenario run")
        available_at = item.executed_at or item.created_at
        if item.forecast_run_id != forecast_run_id or item.dataset_id != dataset_id:
            raise DataStudioError(
                "explanation_source_mismatch",
                "The scenario is not compatible with the selected forecast run.",
                409,
            )
        if _utc(item.created_at) > cutoff or _utc(available_at) > cutoff:
            raise DataStudioError(
                "explanation_future_source",
                "The scenario was not available at the explanation cutoff.",
                409,
            )
        layers["scenario"] = {
            "id": item.id,
            "name": item.name,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
            "available_at": available_at.isoformat(),
            "summary": item.summary_json,
            "warnings": item.warnings,
            "hypothetical": True,
        }
    if scor_assessment_id:
        item = (
            db.query(ScorAssessmentRun)
            .filter(ScorAssessmentRun.id == scor_assessment_id)
            .one_or_none()
        )
        if item is None:
            raise _not_found("scor_assessment_not_found", "SCOR assessment")
        if item.source_dataset_id not in {None, dataset_id} or item.forecast_run_id not in {
            None,
            forecast_run_id,
        }:
            raise DataStudioError(
                "explanation_source_mismatch",
                "The SCOR assessment is not compatible with the selected forecast run.",
                409,
            )
        available_at = item.calculated_at or item.created_at
        if (
            item.status != "calculated"
            or _utc(item.created_at) > cutoff
            or _utc(available_at) > cutoff
            or _utc(item.period_end) > cutoff
        ):
            raise DataStudioError(
                "explanation_future_source",
                "The SCOR assessment was not valid and available at the explanation cutoff.",
                409,
            )
        layers["scor"] = {
            "id": item.id,
            "name": item.name,
            "period_start": item.period_start.isoformat(),
            "period_end": item.period_end.isoformat(),
            "calculated_at": available_at.isoformat(),
            "version": item.algorithm_version,
            "summary": item.summary_json,
            "criticality": item.criticality_json,
        }
    if portfolio_run_id:
        item = db.query(PortfolioRun).filter(PortfolioRun.id == portfolio_run_id).one_or_none()
        if item is None:
            raise _not_found("portfolio_not_found", "portfolio run")
        if (
            item.source_mode != "official"
            or item.dataset_id != dataset_id
            or forecast_run_id not in item.forecast_run_ids
        ):
            raise DataStudioError(
                "explanation_source_mismatch",
                "The portfolio run is not compatible with the selected forecast run.",
                409,
            )
        if (
            _utc(item.created_at) > cutoff
            or _utc(item.available_at) > cutoff
            or _utc(item.cutoff) > cutoff
        ):
            raise DataStudioError(
                "explanation_future_source",
                "The portfolio run was not available at the explanation cutoff.",
                409,
            )
        layers["portfolio"] = {
            "id": item.id,
            "cutoff": item.cutoff.isoformat(),
            "created_at": item.created_at.isoformat(),
            "available_at": item.available_at.isoformat(),
            "version": item.calculation_version,
            "summary": item.summary_json,
            "warnings": item.warnings,
        }
    if decision_run_id:
        item = db.query(DecisionRun).filter(DecisionRun.id == decision_run_id).one_or_none()
        if item is None:
            raise _not_found("decision_run_not_found", "decision run")
        if item.forecast_run_id != forecast_run_id or item.dataset_id != dataset_id:
            raise DataStudioError(
                "explanation_source_mismatch",
                "The decision run is not compatible with the selected forecast run.",
                409,
            )
        if _utc(item.created_at) > cutoff or _utc(item.decision_cutoff) > cutoff:
            raise DataStudioError(
                "explanation_future_source",
                "The decision run was not available at the explanation cutoff.",
                409,
            )
        decision_portfolio = (item.source_snapshot or {}).get("portfolio")
        associated_portfolio_id = (
            decision_portfolio.get("portfolio_run_id")
            if isinstance(decision_portfolio, dict)
            else None
        )
        if portfolio_run_id and associated_portfolio_id != portfolio_run_id:
            raise DataStudioError(
                "explanation_source_mismatch",
                "The portfolio run is not associated with the selected decision run.",
                409,
            )
        layers["decision"] = {
            "id": item.id,
            "decision_cutoff": item.decision_cutoff.isoformat(),
            "created_at": item.created_at.isoformat(),
            "summary": item.summary_json,
            "warnings": item.warnings,
            "recommendation_count": len(item.recommendations),
        }
        layers["context"] = (item.source_snapshot or {}).get("context")
    return layers
