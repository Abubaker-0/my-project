"""Store student documents on local disk with a checked file type."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.exceptions import AppException

_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def sniff(data: bytes) -> tuple[str, str]:
    """Return the content type and extension for a PDF or image payload."""
    if data.startswith(b"%PDF-"):
        return "application/pdf", ".pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    raise AppException(
        422,
        "VALIDATION_ERROR",
        "Upload a PDF, JPEG, PNG, or WebP file",
        details=[{"field": "file", "message": "Unsupported file type"}],
    )


def save_document(data: bytes, original_name: str | None) -> tuple[str, str, str]:
    """Write the bytes and return `(original name, relative path, content type)`."""
    settings = get_settings()
    if not data:
        raise AppException(
            422,
            "VALIDATION_ERROR",
            "The file is empty",
            details=[{"field": "file", "message": "Choose a file"}],
        )
    if len(data) > settings.max_upload_bytes:
        raise AppException(
            422,
            "VALIDATION_ERROR",
            "The file is larger than 5 MB",
            details=[{"field": "file", "message": "Maximum size is 5 MB"}],
        )
    content_type, extension = sniff(data)
    relative = f"documents/{uuid4().hex}{extension}"
    destination = settings.upload_path / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return _display_name(original_name, extension), relative, content_type


def absolute_path(stored_path: str) -> Path:
    """Resolve a stored relative path and refuse anything outside the upload root."""
    root = get_settings().upload_path.resolve()
    full = (root / stored_path).resolve()
    if not full.is_relative_to(root) or not full.is_file():
        raise AppException(404, "NOT_FOUND", "Document file not found")
    return full


def _display_name(original_name: str | None, extension: str) -> str:
    raw = (original_name or "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
    cleaned = _NAME.sub("-", raw).strip(".-")[:180]
    if not cleaned:
        return f"document{extension}"
    return cleaned
