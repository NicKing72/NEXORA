"""Environment-driven application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseSettings


def _default_database_url() -> str:
    repository_root = Path(__file__).resolve().parents[5]
    database_path = (repository_root / "data" / "nexora.db").as_posix()
    return f"sqlite:///{database_path}"


class Settings(BaseSettings):
    """Runtime settings with safe development defaults."""

    app_name: str = "NEXORA API"
    environment: str = "development"
    database_url: str = _default_database_url()
    cors_origins: list[str] = ["http://localhost:3000"]
    max_upload_bytes: int = 50 * 1024 * 1024
    preview_rows: int = 30
    storage_root: Path = Path(__file__).resolve().parents[5] / "data"

    class Config:
        """Pydantic environment loading behavior."""

        env_file = ".env"
        env_prefix = "NEXORA_"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Return one configuration source per process."""
    return Settings()
