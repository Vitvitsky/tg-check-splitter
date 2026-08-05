import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.models.base import Base
from tests.db import make_test_engine
from tests.env import apply_test_env


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch):
    """No test may read the developer's own .env — see tests/env.py for the bug."""
    apply_test_env(monkeypatch)
    yield
    from core.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
async def db_session():
    engine = make_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()
