"""Shared response shapes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer

T = TypeVar("T")


def _as_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


UtcDateTime = Annotated[
    datetime,
    PlainSerializer(_as_utc_iso, return_type=str, when_used="json"),
]


class APIModel(BaseModel):
    """Base schema that reads ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(APIModel):
    field: str
    message: str


class ErrorBody(APIModel):
    """Standard error envelope: `{code, message, details}`."""

    code: str
    message: str
    details: Any = None


class Page(APIModel, Generic[T]):
    """Standard list envelope."""

    items: list[T]
    total: int
    page: int
    page_size: int


class MessageResponse(APIModel):
    message: str
