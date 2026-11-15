"""Structured-enough text logs that always carry the request id."""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.context import request_id_ctx


class RequestIdFilter(logging.Filter):
    """Attach the current request id to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get("-")
        return True


def setup_logging() -> None:
    """Configure the root logger once for the API process."""
    settings = get_settings()
    if settings.app_env == "development":
        level = logging.DEBUG
    elif settings.app_env == "test":
        level = logging.WARNING
    else:
        level = logging.INFO

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
        )
    )
    handler.addFilter(RequestIdFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
