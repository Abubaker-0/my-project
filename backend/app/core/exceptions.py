"""Application errors mapped to the standard API error envelope."""

from __future__ import annotations

from typing import Any


class AppException(Exception):
    """A domain or request error with a stable machine code."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    """Build the `{code, message, details}` body required by the API contract."""
    return {"code": code, "message": message, "details": details}
