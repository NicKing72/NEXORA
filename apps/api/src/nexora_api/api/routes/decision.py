"""Versioned endpoints for explainable, non-executing decision support."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from nexora_api.db.session import get_database_session
from nexora_api.schemas.decision import (
    DecisionComparisonResponse,
    DecisionEvidenceResponse,
    DecisionPreflightResponse,
    DecisionRecommendationResponse,
    DecisionRequest,
    DecisionRunResponse,
    DecisionRunSummary,
    DecisionStatusUpdate,
)
from nexora_api.services.decisions.service import (
    change_status,
    comparison,
    generate_decision_run,
    list_runs,
    preflight,
    require_recommendation,
    require_run,
    serialize_evidence,
    serialize_recommendation,
    serialize_run,
)

router = APIRouter(prefix="/api/v1/decisions", tags=["decision-engine"])


@router.post("/preflight", response_model=DecisionPreflightResponse)
def decision_preflight(
    payload: DecisionRequest, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return preflight(db, payload.forecast_run_id, payload.scenario_run_id, payload.decision_cutoff)


@router.post("", response_model=DecisionRunResponse, status_code=status.HTTP_201_CREATED)
def create_decision_run(
    payload: DecisionRequest, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    run = generate_decision_run(
        db, payload.forecast_run_id, payload.scenario_run_id, payload.decision_cutoff
    )
    return serialize_run(run)


@router.get("", response_model=list[DecisionRunSummary])
def retrieve_runs(db: Session = Depends(get_database_session)) -> list[dict[str, object]]:
    return list_runs(db)


@router.get("/recommendations/{recommendation_id}", response_model=DecisionRecommendationResponse)
def retrieve_recommendation(
    recommendation_id: UUID, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_recommendation(require_recommendation(db, str(recommendation_id)))


@router.get(
    "/recommendations/{recommendation_id}/evidence",
    response_model=list[DecisionEvidenceResponse],
)
def retrieve_evidence(
    recommendation_id: UUID, db: Session = Depends(get_database_session)
) -> list[dict[str, object]]:
    recommendation = require_recommendation(db, str(recommendation_id))
    return [
        serialize_evidence(item)
        for item in sorted(recommendation.evidence, key=lambda item: item.id)
    ]


@router.patch(
    "/recommendations/{recommendation_id}/status",
    response_model=DecisionRecommendationResponse,
)
def update_recommendation_status(
    recommendation_id: UUID,
    payload: DecisionStatusUpdate,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    return serialize_recommendation(
        change_status(db, str(recommendation_id), payload.status, payload.note)
    )


@router.get("/{run_id}", response_model=DecisionRunResponse)
def retrieve_run(run_id: UUID, db: Session = Depends(get_database_session)) -> dict[str, object]:
    return serialize_run(require_run(db, str(run_id)))


@router.get("/{run_id}/recommendations", response_model=list[DecisionRecommendationResponse])
def retrieve_run_recommendations(
    run_id: UUID, db: Session = Depends(get_database_session)
) -> list[dict[str, object]]:
    run = require_run(db, str(run_id))
    return [
        serialize_recommendation(item)
        for item in sorted(run.recommendations, key=lambda item: item.rank)
    ]


@router.get("/{run_id}/compare", response_model=DecisionComparisonResponse)
def retrieve_comparison(
    run_id: UUID, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return comparison(require_run(db, str(run_id)))
