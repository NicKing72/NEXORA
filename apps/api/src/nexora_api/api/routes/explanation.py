"""Versioned endpoints for immutable, auditable forecast explanations."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from nexora_api.db.session import get_database_session
from nexora_api.schemas.explanation import (
    ExplanationBacktestingResponse,
    ExplanationEvidenceResponse,
    ExplanationForecastResponse,
    ExplanationModelsResponse,
    ExplanationPreflightResponse,
    ExplanationProvenanceResponse,
    ExplanationRequest,
    ExplanationRunResponse,
    ExplanationRunSummary,
    ModelDefinitionResponse,
)
from nexora_api.services.explanations.model_explanation import list_definitions
from nexora_api.services.explanations.service import (
    backtesting_view,
    create_run,
    forecast_view,
    list_runs,
    model_view,
    preflight,
    provenance_view,
    require_run,
    serialize_evidence,
    serialize_run,
)

router = APIRouter(prefix="/api/v1/explanations", tags=["explanation-engine"])


def _request(payload: ExplanationRequest) -> dict[str, object]:
    return payload.dict()


@router.get("/definitions", response_model=list[ModelDefinitionResponse])
def retrieve_definitions() -> list[dict[str, object]]:
    return list_definitions()


@router.post("/preflight", response_model=ExplanationPreflightResponse)
def explanation_preflight(
    payload: ExplanationRequest, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return preflight(db, **_request(payload))


@router.post("", response_model=ExplanationRunResponse, status_code=status.HTTP_201_CREATED)
def create_explanation(
    payload: ExplanationRequest, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_run(create_run(db, **_request(payload)))


@router.get("", response_model=list[ExplanationRunSummary])
def retrieve_runs(db: Session = Depends(get_database_session)) -> list[dict[str, object]]:
    return list_runs(db)


@router.get("/{run_id}", response_model=ExplanationRunResponse)
def retrieve_run(run_id: UUID, db: Session = Depends(get_database_session)) -> dict[str, object]:
    return serialize_run(require_run(db, str(run_id)))


@router.get("/{run_id}/evidence", response_model=list[ExplanationEvidenceResponse])
def retrieve_evidence(
    run_id: UUID, db: Session = Depends(get_database_session)
) -> list[dict[str, object]]:
    run = require_run(db, str(run_id))
    return [serialize_evidence(item) for item in sorted(run.evidence, key=lambda item: item.id)]


@router.get("/{run_id}/models", response_model=ExplanationModelsResponse)
def retrieve_models(run_id: UUID, db: Session = Depends(get_database_session)) -> dict[str, object]:
    return model_view(require_run(db, str(run_id)))


@router.get("/{run_id}/backtesting", response_model=ExplanationBacktestingResponse)
def retrieve_backtesting(
    run_id: UUID, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return backtesting_view(require_run(db, str(run_id)))


@router.get("/{run_id}/forecast", response_model=ExplanationForecastResponse)
def retrieve_forecast(
    run_id: UUID, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return forecast_view(require_run(db, str(run_id)))


@router.get("/{run_id}/provenance", response_model=ExplanationProvenanceResponse)
def retrieve_provenance(
    run_id: UUID, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return provenance_view(require_run(db, str(run_id)))
