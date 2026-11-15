"""In-process scheduler. Invoice reminders and alerts arrive in later phases."""

from __future__ import annotations

import logging
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.time import utcnow
from app.db.session import get_session_factory
from app.repositories.token_repository import TokenRepository

logger = logging.getLogger(__name__)


def purge_expired_refresh_tokens() -> None:
    """Delete refresh tokens that have been expired for at least a day.

    Login and logout events stay in the audit log. The token rows themselves
    are secrets-at-rest bookkeeping, not business records.
    """
    session = get_session_factory()()
    try:
        removed = TokenRepository(session).delete_expired(utcnow() - timedelta(days=1))
        session.commit()
        if removed:
            logger.info("Removed %s expired refresh tokens", removed)
    except Exception:
        session.rollback()
        logger.exception("Refresh token purge failed")
    finally:
        session.close()


def start_scheduler() -> BackgroundScheduler:
    """Start the background scheduler with the foundation maintenance job."""
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        purge_expired_refresh_tokens,
        trigger="interval",
        hours=6,
        id="purge_refresh_tokens",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler
