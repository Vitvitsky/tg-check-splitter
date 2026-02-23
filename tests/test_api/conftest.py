"""Fixtures for FastAPI integration tests.

Provides:
- make_init_data(): generates valid Telegram Mini App initData with correct HMAC
- test_settings: Settings instance with test values (no .env required)
- db_session: async SQLAlchemy session backed by in-memory SQLite
- client: httpx.AsyncClient wired to the FastAPI app with dependency overrides
- auth_headers: Authorization headers with valid initData for the default test user
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import patch
from urllib.parse import urlencode

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.models.base import Base

TEST_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"


def make_init_data(
    user_id: int = 12345,
    first_name: str = "Test",
    auth_date: int | None = None,
    **user_kwargs: object,
) -> str:
    """Build a valid Telegram Mini App initData string for testing.

    The generated string contains a ``user`` JSON, ``auth_date``, ``query_id``,
    and a valid HMAC-SHA256 ``hash`` computed with :data:`TEST_BOT_TOKEN`.
    """
    user = {"id": user_id, "first_name": first_name, **user_kwargs}
    params = {
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "test_query_id",
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", TEST_BOT_TOKEN.encode(), hashlib.sha256).digest()
    hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = hash_value
    return urlencode(params)


@pytest.fixture
def test_settings():
    """Settings instance with test bot token — no .env file required."""
    from bot.config import Settings

    return Settings(
        bot_token=TEST_BOT_TOKEN,
        openrouter_api_key="test-key",
        database_url="sqlite+aiosqlite://",
        webapp_url="http://localhost:5173",
    )


@pytest.fixture
async def db_session():
    """Async SQLAlchemy session backed by an in-memory SQLite database.

    Creates all tables before yielding and disposes of the engine afterwards.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def client(db_session, test_settings):
    """httpx.AsyncClient wired to the FastAPI app with dependency overrides.

    * ``get_db`` yields the test ``db_session`` (in-memory SQLite).
    * ``get_settings`` returns ``test_settings`` everywhere — both as a FastAPI
      dependency and when called directly inside application code (e.g.
      ``api.auth.get_current_user``).
    """
    from api.app import create_app
    from api.deps import get_db

    # Monkeypatch get_settings globally so that *all* call sites
    # (including direct calls like `get_settings().bot_token` in auth.py
    # and `get_settings()` in create_app) receive the test settings.
    # We patch both `bot.config` (canonical location) and `api.auth`
    # (already-imported reference) to ensure the test settings are used
    # regardless of import order.
    from unittest.mock import AsyncMock

    mock_notifier = AsyncMock()
    mock_notifier.notify_member_joined = AsyncMock(return_value=True)
    mock_notifier.notify_settle = AsyncMock()

    with (
        patch("bot.config.get_settings", return_value=test_settings),
        patch("api.auth.get_settings", return_value=test_settings),
        patch("api.routes.sessions.NotificationService", return_value=mock_notifier),
    ):
        app = create_app()

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def auth_headers():
    """Authorization headers with valid initData for the default test user."""
    init_data = make_init_data()
    return {"Authorization": f"tma {init_data}"}
