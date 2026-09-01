"""Versioned Inventory & Replenishment Engine API."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from nexora_api.db.session import get_database_session
from nexora_api.schemas.inventory import (
    InventoryDefinitionsResponse,
    InventoryItemResponse,
    InventoryPreflightResponse,
    InventoryRequest,
    InventoryRunResponse,
    InventoryRunSummary,
)
from nexora_api.services.inventory.service import (
    create_inventory,
    definitions,
    inventory_preflight,
    list_inventory_runs,
    regenerate_demo,
    require_inventory,
    serialize_inventory,
    serialize_item,
)

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory-engine"])


@router.get("/definitions", response_model=InventoryDefinitionsResponse)
def retrieve_definitions() -> dict[str, object]:
    return definitions()


@router.post("/preflight", response_model=InventoryPreflightResponse)
def preflight(
    payload: InventoryRequest, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return inventory_preflight(db, payload)


@router.post("", response_model=InventoryRunResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: InventoryRequest, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_inventory(create_inventory(db, payload))


@router.get("", response_model=list[InventoryRunSummary])
def retrieve_many(db: Session = Depends(get_database_session)) -> list[dict[str, object]]:
    return list_inventory_runs(db)


@router.post("/demo/regenerate", response_model=InventoryRunResponse)
def demo(db: Session = Depends(get_database_session)) -> dict[str, object]:
    return serialize_inventory(regenerate_demo(db))


@router.get("/{run_id}", response_model=InventoryRunResponse)
def retrieve(run_id: str, db: Session = Depends(get_database_session)) -> dict[str, object]:
    return serialize_inventory(require_inventory(db, run_id))


@router.get("/{run_id}/items", response_model=list[InventoryItemResponse])
def retrieve_items(
    run_id: str, db: Session = Depends(get_database_session)
) -> list[dict[str, object]]:
    return [serialize_item(item) for item in require_inventory(db, run_id).items]


@router.get("/{run_id}/summary", response_model=dict[str, object])
def retrieve_summary(run_id: str, db: Session = Depends(get_database_session)) -> dict[str, object]:
    return require_inventory(db, run_id).summary_json


@router.get("/{run_id}/evidence", response_model=dict[str, object])
def retrieve_evidence(
    run_id: str, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    run = require_inventory(db, run_id)
    return {
        "source_snapshot": run.source_snapshot,
        "items": [item.evidence_json for item in run.items],
    }
