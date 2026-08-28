"""FastAPI application factory for NEXORA."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nexora_api import __version__
from nexora_api.api.router import api_router
from nexora_api.core.config import get_settings
from nexora_api.db.session import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prepare local infrastructure before serving requests."""
    initialize_database()
    yield


def create_app() -> FastAPI:
    """Create a configured API instance without business-domain behavior."""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        description="Foundation API for the NEXORA Demand Intelligence System.",
        version=__version__,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router)
    return application


app = create_app()
