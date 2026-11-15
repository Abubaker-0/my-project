"""Refresh tokens and password-reset tokens. Only hashes are stored."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import MYSQL_TABLE_ARGS, Base
from app.db.types import bigint_fk, bigint_pk


class RefreshToken(Base):
    """One session. Rotation links a used token to its replacement."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (MYSQL_TABLE_ARGS,)

    id: Mapped[int] = bigint_pk()
    user_id: Mapped[int] = bigint_fk("users.id", ondelete="CASCADE")
    family_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    replaced_by_id: Mapped[int | None] = bigint_fk(
        "refresh_tokens.id", nullable=True, ondelete="SET NULL"
    )
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class PasswordReset(Base):
    """A single-use password reset secret."""

    __tablename__ = "password_resets"
    __table_args__ = (MYSQL_TABLE_ARGS,)

    id: Mapped[int] = bigint_pk()
    user_id: Mapped[int] = bigint_fk("users.id", ondelete="CASCADE")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user: Mapped[User] = relationship()


from app.models.user import User  # noqa: E402
