"""Versioned Scenario Engine endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from nexora_api.db.session import get_database_session
from nexora_api.schemas.scenario import (
    ScenarioAssumptionResponse,
    ScenarioCreateRequest,
    ScenarioPointResponse,
    ScenarioPreflightRequest,
    ScenarioPreflightResponse,
    ScenarioRunResponse,
    ScenarioRunSummary,
)
from nexora_api.services.scenarios.service import (
    create_scenario,
    execute_scenario,
    list_scenarios,
    preflight,
    require_scenario,
    serialize_assumption,
    serialize_point,
    serialize_scenario,
)

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenario-engine"])


@router.post("/preflight", response_model=ScenarioPreflightResponse)
def scenario_preflight(
    payload: ScenarioPreflightRequest, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return preflight(db, payload.forecast_run_id)


@router.post("", response_model=ScenarioRunResponse, status_code=status.HTTP_201_CREATED)
def create(payload: ScenarioCreateRequest, db: Session = Depends(get_database_session)):
    return serialize_scenario(create_scenario(db, payload))


@router.get("", response_model=list[ScenarioRunSummary])
def retrieve_many(
    forecast_run_id: str | None = Query(None), db: Session = Depends(get_database_session)
):
    return list_scenarios(db, forecast_run_id)


@router.get("/{scenario_id}", response_model=ScenarioRunResponse)
def retrieve(scenario_id: str, db: Session = Depends(get_database_session)):
    return serialize_scenario(require_scenario(db, scenario_id))


@router.post("/{scenario_id}/execute", response_model=ScenarioRunResponse)
def execute(scenario_id: str, db: Session = Depends(get_database_session)):
    return serialize_scenario(execute_scenario(db, scenario_id))


@router.get("/{scenario_id}/assumptions", response_model=list[ScenarioAssumptionResponse])
def retrieve_assumptions(scenario_id: str, db: Session = Depends(get_database_session)):
    run = require_scenario(db, scenario_id)
    return [
        serialize_assumption(item) for item in sorted(run.assumptions, key=lambda x: x.order_index)
    ]


@router.get("/{scenario_id}/points", response_model=list[ScenarioPointResponse])
def retrieve_points(scenario_id: str, db: Session = Depends(get_database_session)):
    run = require_scenario(db, scenario_id)
    return [serialize_point(item) for item in sorted(run.points, key=lambda x: x.timestamp)]


@router.get("/{scenario_id}/compare", response_model=ScenarioRunResponse)
def compare(scenario_id: str, db: Session = Depends(get_database_session)):
    return serialize_scenario(require_scenario(db, scenario_id))
