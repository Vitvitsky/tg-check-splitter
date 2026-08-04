from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str
    zai_api_key: str
    zai_model: str = "glm-4.6v"
    database_url: str
    webapp_url: str = "http://localhost:5173"
    free_scans_per_month: int = 3
    scan_price_stars: int = 1

    # Connection pool. See get_engine() in bot/db.py for why SQLAlchemy's default of 5
    # was too small: opening a connection costs ~80 ms here, a query ~0.2 ms.
    db_pool_size: int = 20
    db_max_overflow: int = 10

    model_config = {"env_file": ".env"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings, built once.

    Cached deliberately: api/auth.py calls this on *every* authenticated request, and
    each uncached call re-parses the environment — and reads .env from disk when the
    file exists. That is synchronous work on the event loop: ~0.5 ms per call inside
    the container, ~1.5 ms locally where .env is present.

    Settings come from the environment, which does not change while the process runs.
    Tests patch this function itself rather than its cache, so the cache cannot hide a
    fixture; anything that legitimately needs to re-read the environment (nothing does
    today) must call get_settings.cache_clear().
    """
    return Settings()
