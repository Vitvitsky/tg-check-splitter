"""Engine construction.

The pool arguments that make PostgreSQL fast are rejected outright by SQLite's
StaticPool/NullPool — create_async_engine raises TypeError rather than ignoring them —
so the two paths have to be kept apart, and both have to be exercised.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

import core.db as db
from core.config import Settings


@pytest.fixture(autouse=True)
def _reset_engine_singleton():
    """get_engine() memoises into a module global; isolate each test from it."""
    db._engine = None
    db._async_session = None
    yield
    db._engine = None
    db._async_session = None


def _settings(url: str, **kwargs) -> Settings:
    return Settings(bot_token="x", zai_api_key="x", database_url=url, **kwargs)


def test_sqlite_engine_builds_without_pool_arguments():
    with patch("core.config.get_settings", return_value=_settings("sqlite+aiosqlite://")):
        engine = db.get_engine()
    assert engine is not None


def test_postgres_engine_uses_the_configured_pool():
    settings = _settings(
        "postgresql+asyncpg://u:p@localhost:5432/x", db_pool_size=7, db_max_overflow=3
    )
    with patch("core.config.get_settings", return_value=settings):
        engine = db.get_engine()

    # A connection costs ~400x a query on this deployment, so the pool must actually be
    # sized from configuration rather than falling back to SQLAlchemy's default of 5.
    assert engine.pool.size() == 7
    assert engine.pool._max_overflow == 3


def test_postgres_engine_pre_pings():
    """Long-lived processes must not hand out a connection the server already dropped."""
    with patch(
        "core.config.get_settings",
        return_value=_settings("postgresql+asyncpg://u:p@localhost:5432/x"),
    ):
        engine = db.get_engine()
    assert engine.pool._pre_ping is True
