"""Hermetic settings for the test suite.

Application code imports the settings accessor by value::

    from core.config import get_settings   # binds the function into this module

so ``patch("core.config.get_settings")`` does **not** reach those call sites — they keep
calling the real function, which reads the developer's own ``.env``. That made test
results depend on the machine they ran on: `test_get_quota` asserts a free allowance of
3 and started failing the moment a developer set ``FREE_SCANS_PER_MONTH=5`` in their
local ``.env``, with nothing in the codebase having changed.

Setting the values as environment variables fixes it at the source instead of at each
call site: pydantic-settings prefers the environment over ``env_file``, so every
``Settings()`` built during a test run — patched or not, whichever module built it —
sees these values. New call sites are covered automatically.
"""

from __future__ import annotations

TEST_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
TEST_FREE_SCANS = 3

TEST_ENV: dict[str, str] = {
    "BOT_TOKEN": TEST_BOT_TOKEN,
    "ZAI_API_KEY": "test-key",
    "ZAI_MODEL": "test-model",
    "DATABASE_URL": "sqlite+aiosqlite://",
    "WEBAPP_URL": "http://localhost:5173",
    "FREE_SCANS_PER_MONTH": str(TEST_FREE_SCANS),
    "SCAN_PRICE_STARS": "1",
}


def apply_test_env(monkeypatch) -> None:
    """Pin the environment and drop any settings cached from a previous value."""
    from core.config import get_settings

    for key, value in TEST_ENV.items():
        monkeypatch.setenv(key, value)
    # get_settings() is lru_cached; a value built before this fixture ran would survive.
    get_settings.cache_clear()
