"""Versioned SCOR diagnostic API."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from nexora_api.db.session import get_database_session
from nexora_api.schemas.scor import (
    ScorAssessmentCreate,
    ScorAssessmentResponse,
    ScorAssessmentSummary,
    ScorBenchmarkApply,
    ScorBenchmarkProfileCreate,
    ScorBenchmarkProfileResponse,
    ScorDefinitionResponse,
    ScorDemoResponse,
    ScorMetricResultResponse,
    ScorProcessResultResponse,
)
from nexora_api.services.scor.definitions import catalog
from nexora_api.services.scor.demo import regenerate_demo
from nexora_api.services.scor.service import (
    apply_benchmark,
    calculate_assessment,
    create_assessment,
    create_profile,
    list_assessments,
    list_profiles,
    require_assessment,
    require_profile,
    serialize_assessment,
    serialize_metric_result,
    serialize_process,
    serialize_profile,
)

router = APIRouter(prefix="/api/v1/scor", tags=["scor-diagnostic"])


@router.get("/definitions", response_model=list[ScorDefinitionResponse])
def definitions() -> list[dict[str, object]]:
    return catalog()


@router.post("/demo/regenerate", response_model=ScorDemoResponse)
def demo_regenerate(db: Session = Depends(get_database_session)) -> dict[str, object]:
    assessment, profile = regenerate_demo(db)
    return {
        "assessment": serialize_assessment(assessment),
        "benchmark_profile": serialize_profile(profile),
    }


@router.get("/benchmark-profiles", response_model=list[ScorBenchmarkProfileResponse])
def benchmark_profiles(db: Session = Depends(get_database_session)) -> list[dict[str, object]]:
    return list_profiles(db)


@router.post(
    "/benchmark-profiles",
    response_model=ScorBenchmarkProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def benchmark_profile_create(
    payload: ScorBenchmarkProfileCreate, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_profile(create_profile(db, payload))


@router.get("/benchmark-profiles/{profile_id}", response_model=ScorBenchmarkProfileResponse)
def benchmark_profile_detail(
    profile_id: str, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_profile(require_profile(db, profile_id))


@router.get("/assessments", response_model=list[ScorAssessmentSummary])
def assessments(db: Session = Depends(get_database_session)) -> list[dict[str, object]]:
    return list_assessments(db)


@router.post(
    "/assessments", response_model=ScorAssessmentResponse, status_code=status.HTTP_201_CREATED
)
def assessment_create(
    payload: ScorAssessmentCreate, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_assessment(create_assessment(db, payload))


@router.get("/assessments/{assessment_id}", response_model=ScorAssessmentResponse)
def assessment_detail(
    assessment_id: str, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_assessment(require_assessment(db, assessment_id))


@router.post("/assessments/{assessment_id}/calculate", response_model=ScorAssessmentResponse)
def assessment_calculate(
    assessment_id: str, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_assessment(calculate_assessment(db, assessment_id))


@router.get("/assessments/{assessment_id}/metrics", response_model=list[ScorMetricResultResponse])
def assessment_metrics(
    assessment_id: str, db: Session = Depends(get_database_session)
) -> list[dict[str, object]]:
    run = require_assessment(db, assessment_id)
    return [
        serialize_metric_result(item)
        for item in sorted(run.metric_results, key=lambda item: item.metric_id)
    ]


@router.get(
    "/assessments/{assessment_id}/processes", response_model=list[ScorProcessResultResponse]
)
def assessment_processes(
    assessment_id: str, db: Session = Depends(get_database_session)
) -> list[dict[str, object]]:
    run = require_assessment(db, assessment_id)
    return [
        serialize_process(item)
        for item in sorted(run.process_results, key=lambda item: item.process)
    ]


@router.post("/assessments/{assessment_id}/benchmark", response_model=ScorAssessmentResponse)
def assessment_benchmark(
    assessment_id: str, payload: ScorBenchmarkApply, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_assessment(apply_benchmark(db, assessment_id, payload.benchmark_profile_id))


@router.get("/assessments/{assessment_id}/criticality", response_model=dict[str, object])
def assessment_criticality(
    assessment_id: str, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return require_assessment(db, assessment_id).criticality_json
