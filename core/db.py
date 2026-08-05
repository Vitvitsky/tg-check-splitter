from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_async_session = None


def get_engine():
    """Lazily build the async engine.

    Pool sizing is the load-bearing part here. Opening a PostgreSQL connection costs
    ~80 ms on this host (measured; scram-sha-256 handshake), while a query on an
    established connection costs ~0.2 ms — the connection is roughly 400x the query.
    With SQLAlchemy's default pool_size of 5, any burst past five simultaneous requests
    had to open overflow connections, and overflow connections are closed again on
    release rather than pooled: a burst paid that ~80 ms over and over. Measured on
    /api/quota: 32 req/s with the default pool.

    Keeping a larger pool warm means the steady-state working set never reopens. The
    ceiling to respect is PostgreSQL's max_connections (100 by default) shared with
    migrations and any psql session — pool_size + max_overflow stays well under it.
    """
    global _engine
    if _engine is None:
        from core.config import get_settings

        settings = get_settings()
        url = settings.database_url
        kwargs: dict = {}
        # SQLite (tests, ad-hoc scripts) uses StaticPool/NullPool, which reject these
        # arguments outright — create_async_engine raises TypeError rather than
        # ignoring them.
        if not url.startswith("sqlite"):
            kwargs = {
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
                # The API and the bot are long-lived; a connection killed server-side or
                # by a restart of the db container would otherwise surface as a failed
                # request instead of a transparent reconnect.
                "pool_pre_ping": True,
                "pool_recycle": 1800,
            }
        _engine = create_async_engine(url, **kwargs)
    return _engine


def get_async_session():
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session
