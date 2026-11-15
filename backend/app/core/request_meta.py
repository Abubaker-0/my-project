"""Client address extraction. Forwarded headers are trusted only when configured."""

from __future__ import annotations

from fastapi import Request

from app.core.config import get_settings


def client_ip(request: Request) -> str | None:
    """Return the caller address.

    `X-Forwarded-For` is ignored unless TRUST_PROXY is enabled, so a client
    cannot spoof the address used for rate limits and the audit log.
    """
    if get_settings().trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
    if request.client is None:
        return None
    return request.client.host[:64]
