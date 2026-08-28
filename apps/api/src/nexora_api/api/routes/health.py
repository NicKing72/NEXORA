"""Service health endpoint."""

from fastapi import APIRouter

from nexora_api.schemas.health import HealthResponse
from nexora_api.services.health import get_health_status

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, summary="Check API health")
def health() -> HealthResponse:
    """Return a lightweight operational status without querying domain data."""
    return get_health_status()
