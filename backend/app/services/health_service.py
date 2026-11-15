"""Liveness of the API process and the database."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app import __version__
from app.core.config import get_settings
from app.repositories.health_repository import HealthRepository
from app.schemas.health import HealthResponse


class HealthService:
    """Reports whether the API can run a query."""

    def __init__(self, session: Session) -> None:
        self.health = HealthRepository(session)

    def check(self) -> HealthResponse:
        """Ping the database and return the public health payload."""
        self.health.ping()
        return HealthResponse(
            status="ok",
            database="ok",
            app=get_settings().app_name,
            version=__version__,
        )
