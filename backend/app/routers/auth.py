"""Authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.core.config import get_settings
from app.core.cookies import REFRESH_COOKIE, clear_refresh_cookie, set_refresh_cookie
from app.core.deps import CurrentActor, DbSession
from app.core.rate_limit import limiter
from app.core.request_meta import client_ip
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SessionResponse,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserSelf
from app.services.auth_service import AuthService
from app.services.presenters import to_user_self

router = APIRouter(prefix="/auth", tags=["auth"])


def _limit(bucket: str, request: Request) -> None:
    settings = get_settings()
    limiter.check(
        f"{bucket}:{client_ip(request) or 'unknown'}",
        settings.login_rate_limit,
        settings.login_rate_window_seconds,
    )


def _presented_refresh(request: Request, explicit: str | None) -> str | None:
    return explicit or request.cookies.get(REFRESH_COOKIE)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest, request: Request, response: Response, db: DbSession
) -> TokenResponse:
    """Exchange a password for an access token and a rotating refresh token."""
    _limit("login", request)
    result = AuthService(db).login(
        email=payload.email,
        password=payload.password,
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    set_refresh_cookie(response, result.refresh_token)
    return result


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request, response: Response, db: DbSession, payload: RefreshRequest | None = None
) -> TokenResponse:
    """Rotate the refresh token presented in the cookie or the JSON body."""
    _limit("refresh", request)
    result = AuthService(db).refresh(
        raw_token=_presented_refresh(request, None if payload is None else payload.refresh_token),
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    set_refresh_cookie(response, result.refresh_token)
    return result


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request, response: Response, db: DbSession, payload: LogoutRequest | None = None
) -> MessageResponse:
    """Revoke the current refresh token."""
    AuthService(db).logout(
        _presented_refresh(request, None if payload is None else payload.refresh_token),
        ip=client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    clear_refresh_cookie(response)
    return MessageResponse(message="Signed out")


@router.post("/logout-all", response_model=MessageResponse)
def logout_all(
    request: Request, response: Response, actor: CurrentActor, db: DbSession
) -> MessageResponse:
    """Revoke every session for the signed-in user."""
    AuthService(db).logout_all(
        actor.id, ip=client_ip(request), user_agent=request.headers.get("user-agent")
    )
    clear_refresh_cookie(response)
    return MessageResponse(message="Signed out of every session")


@router.get("/sessions", response_model=list[SessionResponse])
def sessions(request: Request, actor: CurrentActor, db: DbSession) -> list[SessionResponse]:
    """List the signed-in user's active sessions."""
    return AuthService(db).list_sessions(actor.id, request.cookies.get(REFRESH_COOKIE))


@router.get("/me", response_model=UserSelf)
def me(actor: CurrentActor, db: DbSession) -> UserSelf:
    """Return the signed-in user and the permissions the interface may show."""
    user = UserRepository(db).get(actor.id)
    assert user is not None
    return to_user_self(user, actor)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest, request: Request, db: DbSession
) -> MessageResponse:
    """Start a password reset. The response does not reveal whether the email exists."""
    _limit("forgot", request)
    AuthService(db).forgot_password(payload.email, ip=client_ip(request))
    return MessageResponse(message="If the account exists, a reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest, request: Request, db: DbSession
) -> MessageResponse:
    """Set a new password with a single-use reset token."""
    _limit("reset", request)
    AuthService(db).reset_password(
        token=payload.token, password=payload.password, ip=client_ip(request)
    )
    return MessageResponse(message="Password updated. Sign in with the new password")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    actor: CurrentActor,
    db: DbSession,
) -> MessageResponse:
    """Change the signed-in user's password and revoke existing sessions."""
    AuthService(db).change_password(
        user_id=actor.id,
        current_password=payload.current_password,
        new_password=payload.new_password,
        ip=client_ip(request),
    )
    clear_refresh_cookie(response)
    return MessageResponse(message="Password updated. Sign in again")
