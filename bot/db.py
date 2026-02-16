from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_async_session = None


def get_engine():
    global _engine
    if _engine is None:
        from bot.config import get_settings

        _engine = create_async_engine(get_settings().database_url)
    return _engine


def get_async_session():
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session
