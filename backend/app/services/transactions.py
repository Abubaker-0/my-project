"""Commit helper used by every service."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException


def commit_or_conflict(session: Session) -> None:
    """Commit the current transaction, translating unique-constraint races."""
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise AppException(
            409,
            "CONFLICT",
            "The record conflicts with existing data",
        ) from exc
