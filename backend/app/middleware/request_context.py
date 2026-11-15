"""Attach a request id, client IP, and user agent to the audit context.

This is plain ASGI middleware so the context variables stay on the same task
as the endpoint. `BaseHTTPMiddleware` can drop them.
"""

from __future__ import annotations

import re
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.context import client_ip_ctx, request_id_ctx, user_agent_ctx
from app.core.request_meta import client_ip

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestContextMiddleware:
    """Seed the audit context and echo `X-Request-ID` on the response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive=receive)
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID.fullmatch(incoming) else uuid4().hex
        user_agent = request.headers.get("user-agent")
        token_id = request_id_ctx.set(request_id)
        token_ip = client_ip_ctx.set(client_ip(request))
        token_ua = user_agent_ctx.set(None if not user_agent else user_agent[:500])

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_id_ctx.reset(token_id)
            client_ip_ctx.reset(token_ip)
            user_agent_ctx.reset(token_ua)


class SecurityHeadersMiddleware:
    """Add a small set of response headers on every API response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "no-referrer"
                headers["X-Permitted-Cross-Domain-Policies"] = "none"
            await send(message)

        await self.app(scope, receive, send_with_headers)
