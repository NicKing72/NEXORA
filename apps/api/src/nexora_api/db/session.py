"""SQLAlchemy engine and request-scoped session helpers."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from nexora_api import models as _models  # noqa: F401
from nexora_api.core.config import get_settings
from nexora_api.db.base import Base

settings = get_settings()
sqlite_options = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine: Engine = create_engine(settings.database_url, connect_args=sqlite_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def initialize_database() -> None:
    """Create the SQLite folder and any registered tables."""
    if settings.database_url.startswith("sqlite"):
        database_path = settings.database_url.removeprefix("sqlite:///")
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    if settings.database_url.startswith("sqlite"):
        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA optimize")


def get_database_session() -> Generator[Session, None, None]:
    """Provide a database session that always closes after a request."""
    with SessionLocal() as session:
        yield session
