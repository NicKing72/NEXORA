"""Versioned API for persisted operational portfolio diagnostics."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from nexora_api.db.session import get_database_session
from nexora_api.schemas.portfolio import (
    PortfolioDefinitionsResponse,
    PortfolioItemResponse,
    PortfolioPreflightResponse,
    PortfolioRequest,
    PortfolioRunResponse,
    PortfolioRunSummary,
)
from nexora_api.services.portfolio.service import (
    create_portfolio,
    definitions,
    list_portfolios,
    portfolio_preflight,
    regenerate_demo,
    require_portfolio,
    serialize_item,
    serialize_portfolio,
)

router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio-engine"])


@router.get("/definitions", response_model=PortfolioDefinitionsResponse)
def retrieve_definitions() -> dict[str, object]:
    return definitions()


@router.post("/preflight", response_model=PortfolioPreflightResponse)
def preflight(
    payload: PortfolioRequest,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    return portfolio_preflight(db, payload)


@router.post("", response_model=PortfolioRunResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: PortfolioRequest,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    return serialize_portfolio(create_portfolio(db, payload))


@router.get("", response_model=list[PortfolioRunSummary])
def retrieve_many(db: Session = Depends(get_database_session)) -> list[dict[str, object]]:
    return list_portfolios(db)


@router.post("/demo/regenerate", response_model=PortfolioRunResponse)
def demo(db: Session = Depends(get_database_session)) -> dict[str, object]:
    return serialize_portfolio(regenerate_demo(db))


@router.get("/{portfolio_run_id}", response_model=PortfolioRunResponse)
def retrieve(
    portfolio_run_id: str,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    return serialize_portfolio(require_portfolio(db, portfolio_run_id))


@router.get("/{portfolio_run_id}/items", response_model=list[PortfolioItemResponse])
def retrieve_items(
    portfolio_run_id: str,
    db: Session = Depends(get_database_session),
) -> list[dict[str, object]]:
    run = require_portfolio(db, portfolio_run_id)
    ordered = sorted(run.items, key=lambda item: (item.rank, item.series_key))
    return [serialize_item(item) for item in ordered]


@router.get("/{portfolio_run_id}/summary", response_model=dict[str, object])
def retrieve_summary(
    portfolio_run_id: str,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    return require_portfolio(db, portfolio_run_id).summary_json


@router.get("/{portfolio_run_id}/ranking", response_model=list[PortfolioItemResponse])
def retrieve_ranking(
    portfolio_run_id: str,
    db: Session = Depends(get_database_session),
) -> list[dict[str, object]]:
    run = require_portfolio(db, portfolio_run_id)
    ordered = sorted(run.items, key=lambda item: (item.rank, item.series_key))
    return [serialize_item(item) for item in ordered]
