"""Isolated database and filesystem fixtures for Data Studio API tests."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from nexora_api.api.routes.data_studio import get_storage_service
from nexora_api.db.base import Base
from nexora_api.db.session import get_database_session
from nexora_api.main import app
from nexora_api.services.data_studio.storage import StorageService


@pytest.fixture
def storage(tmp_path: Path) -> StorageService:
    return StorageService(tmp_path / "data", max_upload_bytes=2 * 1024 * 1024)


@pytest.fixture
def client(storage: StorageService) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    def override_database() -> Generator[Session, None, None]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database
    app.dependency_overrides[get_storage_service] = lambda: storage
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
