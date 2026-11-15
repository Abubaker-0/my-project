"""Columns required on business records."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow


class TimestampMixin:
    """Creation and update timestamps maintained by the ORM."""

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


class AuditUserMixin(TimestampMixin):
    """Soft delete plus the users who created and last changed the row.

    `created_by` and `updated_by` are indexed user ids without a foreign key so
    the first seeded account and the audit history can outlive a deleted login.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
