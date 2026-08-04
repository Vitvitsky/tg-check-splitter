"""Shared test database helper.

SQLite ignores foreign keys unless ``PRAGMA foreign_keys=ON`` is issued per
connection. Without it the test suite silently accepts deletes that Postgres
rejects — which is exactly how the missing ON DELETE rules on sessions/items
shipped to production with 109 green tests. Every test engine goes through
:func:`make_test_engine` so the pragma can never be forgotten again.
"""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def make_test_engine(url: str = "sqlite+aiosqlite:///:memory:") -> AsyncEngine:
    """Create an async SQLite engine with foreign key enforcement enabled."""
    engine = create_async_engine(url)

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine
