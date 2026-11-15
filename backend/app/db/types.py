"""Column helpers that stay valid on MariaDB 10.4 and on the SQLite test database."""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.orm import mapped_column

MONEY = Numeric(12, 2)


def pk_type():
    """Primary-key type.

    MariaDB stores BIGINT UNSIGNED. SQLite only auto-increments a column when
    its type is exactly INTEGER, so the test database uses that instead.
    """
    return (
        BigInteger()
        .with_variant(Integer(), "sqlite")
        .with_variant(MYSQL_BIGINT(unsigned=True), "mysql")
    )


def _bigint():
    return pk_type()


def bigint_pk():
    """Primary key. MySQL uses BIGINT UNSIGNED; other dialects use BIGINT."""
    return mapped_column(_bigint(), primary_key=True, autoincrement=True)


def bigint_fk(target: str, *, nullable: bool = False, ondelete: str = "RESTRICT"):
    """Foreign key whose type matches the unsigned primary keys on MySQL."""
    return mapped_column(
        _bigint(),
        ForeignKey(target, ondelete=ondelete),
        nullable=nullable,
        index=True,
    )
