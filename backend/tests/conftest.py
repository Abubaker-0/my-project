"""SQLite fixtures. Production and local development use MariaDB; tests stay offline."""

from __future__ import annotations

import os

os.environ["APP_ENV"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["START_SCHEDULER"] = "false"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["FRONTEND_URL"] = "http://localhost:5173"
os.environ["COOKIE_SECURE"] = "false"
os.environ["SEED_ADMIN_EMAIL"] = "admin@tuition.example"
os.environ["SEED_ADMIN_PASSWORD"] = "Admin@12345"
os.environ["SEED_ADMIN_NAME"] = "System Administrator"
os.environ["LOGIN_RATE_LIMIT"] = "1000"
os.environ["MAX_FAILED_LOGINS"] = "5"

import app.models  # noqa: F401
import pytest
from app.core.rate_limit import limiter
from app.db.base import Base
from app.db.seed import seed
from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_fks(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    limiter.reset()

    def _override():
        try:
            yield db_session
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    limiter.reset()


@pytest.fixture
def admin_headers(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tuition.example", "password": "Admin@12345"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
