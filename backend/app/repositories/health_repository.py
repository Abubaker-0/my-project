"""Connectivity check used by the health endpoint."""

from __future__ import annotations

from sqlalchemy import text

from app.repositories.base import Repository


class HealthRepository(Repository):
    """Runs the one query the health check needs."""

    def ping(self) -> bool:
        self.session.execute(text("SELECT 1"))
        return True
