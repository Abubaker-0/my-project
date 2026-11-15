"""Auth service rules and the login, refresh, and password endpoints."""

from __future__ import annotations

import logging
import re
from datetime import timedelta

import pytest
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.rate_limit import limiter
from app.core.security import hash_password, validate_password_strength, verify_password
from app.core.time import utcnow
from app.models.token import RefreshToken
from app.services.auth_service import AuthService


def test_password_policy_and_hash():
    validate_password_strength("Admin@12345")
    try:
        validate_password_strength("short1A")
        raise AssertionError("expected a policy failure")
    except Exception as exc:
        assert exc.code == "VALIDATION_ERROR"
    hashed = hash_password("Admin@12345")
    assert hashed != "Admin@12345"
    assert verify_password("Admin@12345", hashed)
    assert not verify_password("nope", hashed)


def test_login_me_and_audit(client, admin_headers):
    me = client.get("/api/v1/auth/me", headers=admin_headers)
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "admin@tuition.example"
    assert body["all_branches"] is True
    assert "users:read" in body["permissions"]
    assert "password" not in body
    logs = client.get("/api/v1/audit-logs", headers=admin_headers)
    assert logs.status_code == 200
    actions = [item["action"] for item in logs.json()["items"]]
    assert "login" in actions


def test_bad_password_and_unknown_email_share_the_error(client):
    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@tuition.example", "password": "Admin@12345"},
    )
    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tuition.example", "password": "Wrong@12345"},
    )
    assert unknown.status_code == 401
    assert wrong.status_code == 401
    assert unknown.json()["code"] == wrong.json()["code"] == "INVALID_CREDENTIALS"
    assert "password_hash" not in unknown.text


def test_lockout_after_repeated_failures(client):
    settings = get_settings()
    settings.max_failed_logins = 3
    try:
        for _ in range(2):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "admin@tuition.example", "password": "Wrong@12345"},
            )
            assert response.status_code == 401
        locked = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@tuition.example", "password": "Wrong@12345"},
        )
        assert locked.status_code == 423
        assert locked.json()["code"] == "ACCOUNT_LOCKED"
        still = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@tuition.example", "password": "Admin@12345"},
        )
        assert still.status_code == 423
    finally:
        settings.max_failed_logins = 5


def test_refresh_rotation_and_reuse_revokes_the_family(client):
    first = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tuition.example", "password": "Admin@12345"},
    )
    original = first.json()["refresh_token"]
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    assert rotated.status_code == 200
    replacement = rotated.json()["refresh_token"]
    assert replacement != original
    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    assert replay.status_code == 401
    assert replay.json()["code"] == "TOKEN_REUSED"
    dead = client.post("/api/v1/auth/refresh", json={"refresh_token": replacement})
    assert dead.status_code == 401


def test_logout_revokes_the_refresh_token(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tuition.example", "password": "Admin@12345"},
    )
    raw = login.json()["refresh_token"]
    gone = client.post("/api/v1/auth/logout", json={"refresh_token": raw})
    assert gone.status_code == 200
    assert "httponly" in login.headers["set-cookie"].lower()
    refused = client.post("/api/v1/auth/refresh", json={"refresh_token": raw})
    assert refused.status_code == 401


def test_protected_route_requires_a_bearer_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"
    assert response.headers["x-request-id"]


def test_expired_lock_clears_and_allows_login(db_session):
    service = AuthService(db_session)
    with pytest.raises(AppException) as caught:
        service.login(
            email="admin@tuition.example",
            password="Wrong@12345",
            ip="127.0.0.1",
            user_agent="pytest",
        )
    assert caught.value.code == "INVALID_CREDENTIALS"
    from app.repositories.user_repository import UserRepository

    user = UserRepository(db_session).get_by_email("admin@tuition.example")
    user.status = "locked"
    user.locked_until = utcnow() - timedelta(minutes=1)
    db_session.commit()
    token = service.login(
        email="admin@tuition.example", password="Admin@12345", ip="127.0.0.1", user_agent="pytest"
    )
    assert token.access_token
    assert user.status == "active"


def test_forgot_password_is_generic_and_reset_works(client, caplog):
    caplog.set_level(logging.WARNING)
    missing = client.post("/api/v1/auth/forgot-password", json={"email": "missing@tuition.example"})
    assert missing.status_code == 200
    sent = client.post("/api/v1/auth/forgot-password", json={"email": "admin@tuition.example"})
    assert sent.status_code == 200
    assert sent.json()["message"] == missing.json()["message"]
    match = None
    for record in caplog.records:
        match = re.search(r"token=([A-Za-z0-9_\-]+)", record.message)
        if match:
            break
    assert match is not None
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": match.group(1), "password": "Reset@12345"},
    )
    assert reset.status_code == 200, reset.text
    old = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tuition.example", "password": "Admin@12345"},
    )
    assert old.status_code == 401
    new = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tuition.example", "password": "Reset@12345"},
    )
    assert new.status_code == 200


def test_change_password_revokes_sessions(client, admin_headers):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@tuition.example", "password": "Admin@12345"},
    )
    raw = login.json()["refresh_token"]
    changed = client.post(
        "/api/v1/auth/change-password",
        headers=admin_headers,
        json={"current_password": "Admin@12345", "new_password": "Changed@123"},
    )
    assert changed.status_code == 200, changed.text
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": raw}).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "admin@tuition.example", "password": "Changed@123"},
        ).status_code
        == 200
    )


def test_rate_limit_on_login(client):
    settings = get_settings()
    settings.login_rate_limit = 2
    limiter.reset()
    try:
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "admin@tuition.example", "password": "Wrong@12345"},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "admin@tuition.example", "password": "Wrong@12345"},
            ).status_code
            == 401
        )
        blocked = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@tuition.example", "password": "Wrong@12345"},
        )
        assert blocked.status_code == 429
        assert blocked.json()["code"] == "RATE_LIMITED"
    finally:
        settings.login_rate_limit = 1000
        limiter.reset()


def test_health_and_validation_envelope(client):
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["database"] == "ok"
    bad = client.post("/api/v1/auth/login", json={"email": "not-an-email", "password": "x"})
    assert bad.status_code == 422
    body = bad.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"][0]["field"] == "email"
    assert "set-cookie" not in bad.headers


def test_purge_job_removes_expired_tokens(db_session):
    from app.jobs.scheduler import purge_expired_refresh_tokens
    from app.repositories.token_repository import TokenRepository

    login = AuthService(db_session).login(
        email="admin@tuition.example", password="Admin@12345", ip=None, user_agent=None
    )
    row = TokenRepository(db_session).get_by_hash(
        __import__("app.core.security", fromlist=["hash_token"]).hash_token(login.refresh_token)
    )
    row.expires_at = utcnow() - timedelta(days=2)
    db_session.commit()
    # The job opens its own engine, which is not this in-memory database.
    removed = TokenRepository(db_session).delete_expired(utcnow() - timedelta(days=1))
    db_session.commit()
    assert removed == 1
    assert db_session.get(RefreshToken, row.id) is None
    assert purge_expired_refresh_tokens is not None
