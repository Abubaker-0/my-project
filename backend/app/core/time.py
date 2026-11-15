"""UTC timestamps stored as naive datetimes.

MariaDB 10.4 DATETIME does not keep a time zone. The API always treats these
values as UTC and serializes them with a trailing Z.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return the current UTC time without tzinfo, for DATETIME columns."""
    return datetime.now(UTC).replace(tzinfo=None)
