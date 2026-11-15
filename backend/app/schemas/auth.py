"""Authentication payloads."""

from __future__ import annotations

from pydantic import EmailStr, Field

from app.schemas.common import APIModel, UtcDateTime


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(APIModel):
    """Browsers send an empty body and rely on the HttpOnly cookie."""

    refresh_token: str | None = None


class LogoutRequest(APIModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(APIModel):
    email: EmailStr


class ResetPasswordRequest(APIModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(APIModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class SessionResponse(APIModel):
    id: int
    ip: str | None
    user_agent: str | None
    created_at: UtcDateTime
    expires_at: UtcDateTime
    current: bool
