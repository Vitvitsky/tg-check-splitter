from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from bot.db import get_async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async_session = get_async_session()
    async with async_session() as session:
        yield session
