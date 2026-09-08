"""Versioned product-master and Kardex traceability API."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from nexora_api.db.session import get_database_session
from nexora_api.schemas.kardex import (
    InventoryProductCreate,
    InventoryProductResponse,
    InventoryProductUpdate,
    KardexBalanceResponse,
    KardexDemoResponse,
    KardexMovementCreate,
    KardexMovementPreview,
    KardexMovementResponse,
    KardexSummaryResponse,
)
from nexora_api.services.kardex.balances import product_balance
from nexora_api.services.kardex.demo import regenerate_demo
from nexora_api.services.kardex.export import export_kardex_xlsx
from nexora_api.services.kardex.movements import (
    list_movements,
    preview_movement,
    register_movement,
    require_movement,
    serialize_movement,
)
from nexora_api.services.kardex.products import (
    create_product_with_opening,
    list_products,
    lookup_product,
    require_product,
    serialize_product,
    update_product,
)
from nexora_api.services.kardex.summary import build_summary

router = APIRouter(prefix="/api/v1/kardex", tags=["kardex-engine"])


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@router.get("/products", response_model=list[InventoryProductResponse])
def retrieve_products(
    query: str | None = Query(None, max_length=180),
    active: bool | None = None,
    db: Session = Depends(get_database_session),
) -> list[dict[str, object]]:
    products = list_products(db, query=query, active=active)
    return [serialize_product(db, product) for product in products]


@router.post(
    "/products", response_model=InventoryProductResponse, status_code=status.HTTP_201_CREATED
)
def create_product_route(
    payload: InventoryProductCreate, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_product(db, create_product_with_opening(db, payload))


@router.get("/products/lookup", response_model=InventoryProductResponse)
def retrieve_product_by_identifier(
    identifier: str = Query(..., min_length=1, max_length=180),
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    return serialize_product(db, lookup_product(db, identifier))


@router.get("/products/{product_id}", response_model=InventoryProductResponse)
def retrieve_product(
    product_id: UUID, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_product(db, require_product(db, str(product_id)))


@router.patch("/products/{product_id}", response_model=InventoryProductResponse)
def update_product_route(
    product_id: UUID,
    payload: InventoryProductUpdate,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    return serialize_product(db, update_product(db, str(product_id), payload))


@router.get("/products/{product_id}/balance", response_model=KardexBalanceResponse)
def retrieve_balance(
    product_id: UUID,
    cutoff: datetime | None = None,
    db: Session = Depends(get_database_session),
) -> dict[str, object]:
    product = require_product(db, str(product_id))
    return product_balance(db, product, cutoff=_aware(cutoff))


@router.get("/products/{product_id}/movements", response_model=list[KardexMovementResponse])
def retrieve_product_movements(
    product_id: UUID,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_database_session),
) -> list[dict[str, object]]:
    return [
        serialize_movement(item)
        for item in list_movements(
            db,
            product_id=str(product_id),
            date_from=_aware(date_from),
            date_to=_aware(date_to),
        )
    ]


@router.post("/movements/preview", response_model=KardexMovementPreview)
def preview(
    payload: KardexMovementCreate, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return preview_movement(db, payload)


@router.post(
    "/movements", response_model=KardexMovementResponse, status_code=status.HTTP_201_CREATED
)
def create_movement(
    payload: KardexMovementCreate, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_movement(register_movement(db, payload))


@router.get("/movements/{movement_id}", response_model=KardexMovementResponse)
def retrieve_movement(
    movement_id: UUID, db: Session = Depends(get_database_session)
) -> dict[str, object]:
    return serialize_movement(require_movement(db, str(movement_id)))


@router.get("/summary", response_model=KardexSummaryResponse)
def retrieve_summary(db: Session = Depends(get_database_session)) -> dict[str, object]:
    return build_summary(db)


@router.post("/demo/regenerate", response_model=KardexDemoResponse)
def demo(db: Session = Depends(get_database_session)) -> dict[str, object]:
    return regenerate_demo(db)


@router.get("/export.xlsx", response_class=Response)
def export(
    product_id: UUID | None = None, db: Session = Depends(get_database_session)
) -> StreamingResponse:
    if product_id is not None:
        require_product(db, str(product_id))
    payload = export_kardex_xlsx(db, str(product_id) if product_id else None)
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="nexora-kardex.xlsx"'},
    )
