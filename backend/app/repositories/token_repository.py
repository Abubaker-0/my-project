"""Refresh-token and password-reset persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update

from app.models.token import PasswordReset, RefreshToken
from app.repositories.base import Repository


class TokenRepository(Repository):
    """Stores only hashes. Callers pass the raw token and this class hashes nothing itself."""

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self.session.scalar(stmt)

    def active_for_user(self, user_id: int, now: datetime) -> list[RefreshToken]:
        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .order_by(RefreshToken.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def revoke_family(self, family_id: str, when: datetime) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=when)
        )
        self.session.execute(stmt)

    def revoke_all_for_user(self, user_id: int, when: datetime) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=when)
        )
        self.session.execute(stmt)

    def delete_expired(self, before: datetime) -> int:
        """Hard-delete spent refresh rows. Login events remain in the audit log."""
        stmt = select(RefreshToken).where(RefreshToken.expires_at < before)
        rows = list(self.session.scalars(stmt).all())
        for row in rows:
            self.session.delete(row)
        return len(rows)

    def get_reset_by_hash(self, token_hash: str) -> PasswordReset | None:
        stmt = select(PasswordReset).where(PasswordReset.token_hash == token_hash)
        return self.session.scalar(stmt)
