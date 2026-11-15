"""Email transport. Phase 0 writes to the log; SMTP plugs in behind this interface."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.config import BACKEND_DIR, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    """One outbound message."""

    to: str
    subject: str
    body: str


class EmailAdapter:
    """Transport used by services. Subclasses must not raise for a bad address."""

    def send(self, message: EmailMessage) -> None:
        raise NotImplementedError


class ConsoleEmailAdapter(EmailAdapter):
    """Development transport.

    The message body is written to `backend/var/mail.log` and, when APP_ENV is
    `test`, also to the log so automated tests can read the reset link.
    Production does not write the body. SMTP delivery is a later phase.
    """

    def send(self, message: EmailMessage) -> None:
        settings = get_settings()
        if settings.app_env == "production":
            logger.warning(
                "Email to %s was not delivered because no SMTP transport is configured",
                message.to,
            )
            return
        path = BACKEND_DIR / "var" / "mail.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"TO: {message.to}\nSUBJECT: {message.subject}\n\n{message.body}\n---\n")
        if settings.app_env == "test":
            logger.warning(
                "DEV_EMAIL to=%s subject=%s body=%s", message.to, message.subject, message.body
            )
        else:
            logger.info("Wrote email for %s to %s", message.to, path)
