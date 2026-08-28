"""Health endpoint contracts."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Public health response returned by the API."""

    status: Literal["ok"]
    service: str
    version: str
    environment: str
