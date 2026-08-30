"""Top-level API router."""

from fastapi import APIRouter

from nexora_api.api.routes.context import router as context_router
from nexora_api.api.routes.context_impact import router as context_impact_router
from nexora_api.api.routes.data_studio import router as data_studio_router
from nexora_api.api.routes.decision import router as decision_router
from nexora_api.api.routes.forecast import router as forecast_router
from nexora_api.api.routes.health import router as health_router
from nexora_api.api.routes.scenario import router as scenario_router
from nexora_api.api.routes.scor import router as scor_router
from nexora_api.api.routes.series import router as series_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(context_router)
api_router.include_router(context_impact_router)
api_router.include_router(data_studio_router)
api_router.include_router(decision_router)
api_router.include_router(series_router)
api_router.include_router(forecast_router)
api_router.include_router(scenario_router)
api_router.include_router(scor_router)
