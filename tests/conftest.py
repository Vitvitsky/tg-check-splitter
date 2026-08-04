import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.models.base import Base
from tests.db import make_test_engine


@pytest.fixture
async def db_session():
    engine = make_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()
