"""Password hashing, JWT access tokens, and refresh-token hashing."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.time import utcnow

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")
_PASSWORD_RE_UPPER = re.compile(r"[A-Z]")
_PASSWORD_RE_LOWER = re.compile(r"[a-z]")
_PASSWORD_RE_DIGIT = re.compile(r"\d")
_dummy_hash: str | None = None


def hash_password(password: str) -> str:
    """Hash a password with argon2."""
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True when the password matches the stored argon2 hash."""
    try:
        return _pwd.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


def dummy_verify(password: str) -> None:
    """Spend a hash verification when the account does not exist.

    This keeps the login response time from revealing whether the email is registered.
    """
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("not-a-real-password")
    verify_password(password, _dummy_hash)


def validate_password_strength(password: str) -> None:
    """Enforce the shared password policy."""
    problems: list[dict[str, str]] = []
    if not 8 <= len(password) <= 128:
        problems.append({"field": "password", "message": "Password must be 8 to 128 characters"})
    if not _PASSWORD_RE_UPPER.search(password):
        problems.append(
            {"field": "password", "message": "Password must include an uppercase letter"}
        )
    if not _PASSWORD_RE_LOWER.search(password):
        problems.append(
            {"field": "password", "message": "Password must include a lowercase letter"}
        )
    if not _PASSWORD_RE_DIGIT.search(password):
        problems.append({"field": "password", "message": "Password must include a digit"})
    if problems:
        raise AppException(
            422,
            "VALIDATION_ERROR",
            "Password does not meet the policy",
            details=problems,
        )


def create_access_token(user_id: int) -> tuple[str, int]:
    """Return a signed access token and its lifetime in seconds."""
    settings = get_settings()
    expires_in = settings.access_token_minutes * 60
    now = int(utcnow().timestamp())
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + expires_in,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, expires_in


def decode_access_token(token: str) -> int:
    """Return the user id from a valid access token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise AppException(401, "TOKEN_INVALID", "Access token is invalid or expired") from exc
    if payload.get("type") != "access":
        raise AppException(401, "TOKEN_INVALID", "Access token is invalid or expired")
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AppException(401, "TOKEN_INVALID", "Access token is invalid or expired") from exc


def new_refresh_token() -> str:
    """Return a new unguessable refresh token."""
    return secrets.token_urlsafe(48)


def hash_token(raw_token: str) -> str:
    """Hash a refresh or reset token for storage. Raw tokens are never stored."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def tokens_match(raw_token: str, token_hash: str) -> bool:
    """Compare a presented token with a stored hash."""
    return hmac.compare_digest(hash_token(raw_token), token_hash)


def refresh_expiry():
    """Return the expiry timestamp for a newly issued refresh token."""
    return utcnow() + timedelta(days=get_settings().refresh_token_days)


def reset_expiry():
    """Return the expiry timestamp for a password-reset token."""
    return utcnow() + timedelta(minutes=get_settings().password_reset_minutes)
