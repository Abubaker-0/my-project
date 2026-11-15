"""Shared list-query parameters: page, page_size, sort, and q."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query
from sqlalchemy import asc, desc
from sqlalchemy.sql import ColumnElement

from app.core.exceptions import AppException


@dataclass(frozen=True)
class PageParams:
    """Normalized pagination input."""

    page: int
    page_size: int
    sort: str | None
    q: str | None

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def get_page_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None, max_length=64),
    q: str | None = Query(None, max_length=100),
) -> PageParams:
    """Parse the standard list query string."""
    cleaned = q.strip() if q else None
    return PageParams(page=page, page_size=page_size, sort=sort, q=cleaned or None)


def order_by(sort: str | None, allowed: dict[str, ColumnElement], default: str):
    """Map a sort string such as `-created_at` onto a column expression."""
    raw = sort or default
    descending = raw.startswith("-")
    field = raw[1:] if descending else raw
    column = allowed.get(field)
    if column is None:
        raise AppException(
            400,
            "VALIDATION_ERROR",
            f"Cannot sort by '{field}'",
            details=[{"field": "sort", "message": f"Allowed fields: {', '.join(sorted(allowed))}"}],
        )
    return desc(column) if descending else asc(column)
