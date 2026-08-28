"""Health status service."""

from nexora_api import __version__
from nexora_api.core.config import get_settings
from nexora_api.schemas.health import HealthResponse


def get_health_status() -> HealthResponse:
    """Build the public process health response."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=__version__,
        environment=settings.environment,
    )
