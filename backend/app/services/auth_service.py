"""Sign-in, session rotation, and password recovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.security import (
    create_access_token,
    dummy_verify,
    hash_password,
    hash_token,
    new_refresh_token,
    refresh_expiry,
    reset_expiry,
    validate_password_strength,
    verify_password,
)
from app.core.time import utcnow
from app.integrations.email import ConsoleEmailAdapter, EmailAdapter, EmailMessage
from app.models.token import PasswordReset, RefreshToken
from app.models.user import User
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import SessionResponse, TokenResponse
from app.services.audit_service import AuditService
from app.services.transactions import commit_or_conflict


@dataclass
class _Issued:
    raw: str
    row: RefreshToken


class AuthService:
    """Credential checks and refresh-token families.

    A refresh token is stored only as a SHA-256 hash. Presenting a token that
    was already rotated revokes every session in that family.
    """

    def __init__(self, session: Session, email: EmailAdapter | None = None) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.tokens = TokenRepository(session)
        self.audit = AuditService(session)
        self.email = email or ConsoleEmailAdapter()

    def login(
        self,
        *,
        email: str,
        password: str,
        ip: str | None,
        user_agent: str | None,
    ) -> TokenResponse:
        """Verify a password and open a new session.

        Unknown emails and wrong passwords return the same error. A locked or
        disabled account is reported only after the account is known, and a
        wrong password on a disabled account still looks like a bad password.
        """
        normalized = email.strip().lower()
        user = self.users.get_by_email(normalized)
        if user is None:
            dummy_verify(password)
            self.audit.record(
                action="login",
                entity="user",
                ip=ip,
                user_agent=user_agent,
                new_values={"email": normalized, "success": False, "reason": "unknown"},
            )
            commit_or_conflict(self.session)
            raise AppException(401, "INVALID_CREDENTIALS", "Email or password is incorrect")

        self._clear_expired_lock(user)
        if self._is_locked(user):
            self._login_audit(user, ip, user_agent, success=False, reason="locked")
            commit_or_conflict(self.session)
            raise AppException(
                423,
                "ACCOUNT_LOCKED",
                "This account is temporarily locked. Try again later.",
            )

        if not verify_password(password, user.password_hash):
            self._register_failure(user)
            reason = "locked" if user.status == "locked" else "password"
            self._login_audit(user, ip, user_agent, success=False, reason=reason)
            commit_or_conflict(self.session)
            if user.status == "locked":
                raise AppException(
                    423,
                    "ACCOUNT_LOCKED",
                    "This account is temporarily locked. Try again later.",
                )
            raise AppException(401, "INVALID_CREDENTIALS", "Email or password is incorrect")

        if user.status != "active":
            self._login_audit(user, ip, user_agent, success=False, reason="disabled")
            commit_or_conflict(self.session)
            raise AppException(403, "ACCOUNT_DISABLED", "This account is disabled")

        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = utcnow()
        raw_refresh = self._open_family(user, ip, user_agent)
        access_token, expires_in = create_access_token(user.id)
        self._login_audit(user, ip, user_agent, success=True, reason="ok")
        commit_or_conflict(self.session)
        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=expires_in,
        )

    def refresh(
        self,
        *,
        raw_token: str | None,
        ip: str | None,
        user_agent: str | None,
    ) -> TokenResponse:
        """Rotate a refresh token. Reuse of a revoked token kills the family."""
        if not raw_token:
            raise AppException(401, "TOKEN_INVALID", "Refresh token is invalid or expired")
        row = self.tokens.get_by_hash(hash_token(raw_token))
        if row is None or row.expires_at <= utcnow():
            raise AppException(401, "TOKEN_INVALID", "Refresh token is invalid or expired")
        if row.revoked_at is not None:
            self.tokens.revoke_family(row.family_id, utcnow())
            self.audit.record(
                action="token_reuse",
                entity="user",
                entity_id=row.user_id,
                actor_id=row.user_id,
                ip=ip,
                user_agent=user_agent,
                new_values={"family_id": row.family_id},
            )
            commit_or_conflict(self.session)
            raise AppException(
                401,
                "TOKEN_REUSED",
                "This refresh token was already used. Sign in again.",
            )

        user = self.users.get(row.user_id)
        if user is None or user.status != "active":
            row.revoked_at = utcnow()
            commit_or_conflict(self.session)
            raise AppException(401, "TOKEN_INVALID", "Refresh token is invalid or expired")

        replacement = self._issue_token(
            user_id=user.id,
            family_id=row.family_id,
            ip=ip,
            user_agent=user_agent,
        )
        row.revoked_at = utcnow()
        row.replaced_by_id = replacement.row.id
        access_token, expires_in = create_access_token(user.id)
        commit_or_conflict(self.session)
        return TokenResponse(
            access_token=access_token,
            refresh_token=replacement.raw,
            expires_in=expires_in,
        )

    def logout(self, raw_token: str | None, *, ip: str | None, user_agent: str | None) -> None:
        """Revoke the presented session. Missing cookies still succeed."""
        if raw_token:
            row = self.tokens.get_by_hash(hash_token(raw_token))
            if row is not None and row.revoked_at is None:
                row.revoked_at = utcnow()
                self.audit.record(
                    action="logout",
                    entity="user",
                    entity_id=row.user_id,
                    actor_id=row.user_id,
                    branch_id=self._branch_id(row.user_id),
                    ip=ip,
                    user_agent=user_agent,
                )
        commit_or_conflict(self.session)

    def logout_all(self, user_id: int, *, ip: str | None, user_agent: str | None) -> None:
        """Revoke every active session for the signed-in user."""
        self.tokens.revoke_all_for_user(user_id, utcnow())
        self.audit.record(
            action="logout",
            entity="user",
            entity_id=user_id,
            actor_id=user_id,
            branch_id=self._branch_id(user_id),
            ip=ip,
            user_agent=user_agent,
            new_values={"scope": "all"},
        )
        commit_or_conflict(self.session)

    def list_sessions(self, user_id: int, raw_token: str | None) -> list[SessionResponse]:
        """Return active sessions. The presented refresh token is marked current."""
        current_hash = hash_token(raw_token) if raw_token else None
        rows = self.tokens.active_for_user(user_id, utcnow())
        return [
            SessionResponse(
                id=row.id,
                ip=row.ip,
                user_agent=row.user_agent,
                created_at=row.created_at,
                expires_at=row.expires_at,
                current=row.token_hash == current_hash,
            )
            for row in rows
        ]

    def forgot_password(self, email: str, *, ip: str | None) -> None:
        """Start a reset when the account is active. The response is always generic."""
        normalized = email.strip().lower()
        user = self.users.get_by_email(normalized)
        raw = None
        if user is not None and user.status == "active":
            raw = new_refresh_token()
            self.session.add(
                PasswordReset(
                    user_id=user.id,
                    token_hash=hash_token(raw),
                    expires_at=reset_expiry(),
                )
            )
            self.audit.record(
                action="password_reset_request",
                entity="user",
                entity_id=user.id,
                actor_id=user.id,
                branch_id=self._branch_id(user.id),
                ip=ip,
                new_values={"requested": True},
            )
        commit_or_conflict(self.session)
        if raw is not None:
            link = f"{get_settings().frontend_url}/reset-password?token={raw}"
            self.email.send(
                EmailMessage(
                    to=normalized,
                    subject="Reset your Tuition Center password",
                    body=(
                        "Use the link below to choose a new password. "
                        "It expires shortly and can be used once.\n\n"
                        f"{link}\n"
                    ),
                )
            )

    def reset_password(self, *, token: str, password: str, ip: str | None) -> None:
        """Consume a reset token, replace the password, and revoke sessions."""
        validate_password_strength(password)
        row = self.tokens.get_reset_by_hash(hash_token(token))
        if row is None or row.used_at is not None or row.expires_at <= utcnow():
            raise AppException(400, "TOKEN_INVALID", "Reset token is invalid or expired")
        user = self.users.get(row.user_id)
        if user is None or user.status == "inactive":
            raise AppException(400, "TOKEN_INVALID", "Reset token is invalid or expired")
        self._set_password(user, password)
        row.used_at = utcnow()
        self.tokens.revoke_all_for_user(user.id, utcnow())
        self.audit.record(
            action="password_reset",
            entity="user",
            entity_id=user.id,
            actor_id=user.id,
            branch_id=self._branch_id(user.id),
            ip=ip,
            new_values={"reset": True},
        )
        commit_or_conflict(self.session)

    def change_password(
        self,
        *,
        user_id: int,
        current_password: str,
        new_password: str,
        ip: str | None,
    ) -> None:
        """Replace the password for the signed-in user and revoke other sessions."""
        validate_password_strength(new_password)
        user = self.users.get(user_id)
        if user is None:
            raise AppException(401, "UNAUTHORIZED", "Authentication required")
        if not verify_password(current_password, user.password_hash):
            raise AppException(400, "INVALID_CREDENTIALS", "Current password is incorrect")
        if verify_password(new_password, user.password_hash):
            raise AppException(
                422,
                "VALIDATION_ERROR",
                "Choose a password you have not used before",
                details=[{"field": "new_password", "message": "New password must be different"}],
            )
        self._set_password(user, new_password)
        self.tokens.revoke_all_for_user(user.id, utcnow())
        self.audit.record(
            action="password_change",
            entity="user",
            entity_id=user.id,
            actor_id=user.id,
            branch_id=self._branch_id(user.id),
            ip=ip,
            new_values={"changed": True},
        )
        commit_or_conflict(self.session)

    def _open_family(self, user: User, ip: str | None, user_agent: str | None) -> str:
        issued = self._issue_token(
            user_id=user.id, family_id=str(uuid4()), ip=ip, user_agent=user_agent
        )
        return issued.raw

    def _issue_token(
        self, *, user_id: int, family_id: str, ip: str | None, user_agent: str | None
    ) -> _Issued:
        raw = new_refresh_token()
        row = RefreshToken(
            user_id=user_id,
            family_id=family_id,
            token_hash=hash_token(raw),
            expires_at=refresh_expiry(),
            user_agent=None if not user_agent else user_agent[:255],
            ip=ip,
        )
        self.session.add(row)
        self.session.flush()
        return _Issued(raw=raw, row=row)

    def _register_failure(self, user: User) -> None:
        settings = get_settings()
        user.failed_login_count += 1
        if user.failed_login_count >= settings.max_failed_logins:
            user.status = "locked"
            user.locked_until = utcnow() + timedelta(minutes=settings.lockout_minutes)

    def _clear_expired_lock(self, user: User) -> None:
        if user.locked_until is not None and user.locked_until <= utcnow():
            user.status = "active"
            user.locked_until = None
            user.failed_login_count = 0

    def _is_locked(self, user: User) -> bool:
        if user.locked_until is not None and user.locked_until > utcnow():
            return True
        return user.status == "locked"

    def _set_password(self, user: User, password: str) -> None:
        user.password_hash = hash_password(password)
        user.failed_login_count = 0
        user.locked_until = None
        if user.status == "locked":
            user.status = "active"

    def _login_audit(
        self,
        user: User,
        ip: str | None,
        user_agent: str | None,
        *,
        success: bool,
        reason: str,
    ) -> None:
        self.audit.record(
            action="login",
            entity="user",
            entity_id=user.id,
            actor_id=user.id,
            branch_id=self._branch_of(user),
            ip=ip,
            user_agent=user_agent,
            new_values={"success": success, "reason": reason},
        )

    def _branch_id(self, user_id: int) -> int | None:
        user = self.users.get(user_id)
        return None if user is None else self._branch_of(user)

    @staticmethod
    def _branch_of(user: User) -> int | None:
        for link in user.role_links:
            if link.branch_id is not None:
                return link.branch_id
        return None
