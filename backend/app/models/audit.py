"""Append-only record of security and data changes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import MYSQL_TABLE_ARGS, Base
from app.db.types import bigint_fk, bigint_pk


class AuditLog(Base):
    """One audited action. Rows are never updated or soft-deleted."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_branch_created", "branch_id", "created_at"),
        Index("ix_audit_logs_entity", "entity", "entity_id"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = bigint_pk()
    user_id: Mapped[int | None] = bigint_fk("users.id", nullable=True, ondelete="SET NULL")
    branch_id: Mapped[int | None] = bigint_fk("branches.id", nullable=True, ondelete="SET NULL")
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False, index=True
    )
