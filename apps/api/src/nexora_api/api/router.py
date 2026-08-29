"""Top-level API router."""

from fastapi import APIRouter

from nexora_api.api.routes.data_studio import router as data_studio_router
from nexora_api.api.routes.forecast import router as forecast_router
from nexora_api.api.routes.health import router as health_router
from nexora_api.api.routes.series import router as series_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(data_studio_router)
api_router.include_router(series_router)
api_router.include_router(forecast_router)
