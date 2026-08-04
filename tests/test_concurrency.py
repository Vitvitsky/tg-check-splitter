"""Concurrent-claim tests — PostgreSQL only.

Two people tapping the last portion of a dish at the same moment used to both win:
every claim path read the already-claimed total and then wrote, and under READ
COMMITTED both transactions read "free" before either committed. The unique
constraint does not catch it (it is per item+user, and these are different users),
so the table got billed for two portions of a one-portion dish.

SQLite cannot show any of this: it serialises writers and its dialect does not even
emit FOR UPDATE. These tests therefore need a real PostgreSQL and are skipped without
one. Point TEST_DATABASE_URL at a throwaway database to run them:

    docker compose up -d db
    docker exec tg-check-splitter-db-1 psql -U user -d postgres -c 'CREATE DATABASE racetest;'
    TEST_DATABASE_URL=postgresql+asyncpg://user:password@127.0.0.1:5433/racetest uv run pytest tests/test_concurrency.py
"""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.models.base import Base
from bot.models.session import ItemVote, SessionItem
from bot.services.session import SessionService

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="needs a real PostgreSQL; set TEST_DATABASE_URL (see module docstring)",
)


@pytest.fixture
async def pg_sessionmaker():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


async def _dish(sessionmaker, *, quantity: int):
    async with sessionmaker() as db:
        svc = SessionService(db)
        session = await svc.create_session(1, "Admin")
        items = await svc.save_ocr_items(
            session.id, [{"name": "Pizza", "price": 1000, "quantity": quantity}]
        )
        return session, items[0].id


async def _total_claimed(sessionmaker, item_id) -> int:
    async with sessionmaker() as db:
        rows = await db.execute(select(ItemVote.quantity).where(ItemVote.item_id == item_id))
        return sum(r[0] for r in rows.all())


async def test_simultaneous_taps_cannot_overclaim_a_dish(pg_sessionmaker):
    """Ten users race for a single portion; exactly one may end up holding it."""
    _session, item_id = await _dish(pg_sessionmaker, quantity=1)

    async def tap(user_id: int):
        async with pg_sessionmaker() as db:
            return await SessionService(db).cycle_vote(item_id, user_id, 1)

    results = await asyncio.gather(*(tap(uid) for uid in range(100, 110)))

    assert await _total_claimed(pg_sessionmaker, item_id) == 1
    assert sum(1 for quantity, _overflow in results if quantity > 0) == 1


async def test_simultaneous_taps_fill_a_multi_portion_dish_exactly(pg_sessionmaker):
    """Six users race for three portions: all three go out, none is double-sold."""
    _session, item_id = await _dish(pg_sessionmaker, quantity=3)

    async def tap(user_id: int):
        async with pg_sessionmaker() as db:
            return await SessionService(db).cycle_vote(item_id, user_id, 3)

    await asyncio.gather(*(tap(uid) for uid in range(200, 206)))

    assert await _total_claimed(pg_sessionmaker, item_id) == 3


async def test_set_vote_races_are_also_bounded(pg_sessionmaker):
    """The explicit-quantity path shares the same read-then-write window."""
    _session, item_id = await _dish(pg_sessionmaker, quantity=4)

    async def claim(user_id: int, qty: int):
        async with pg_sessionmaker() as db:
            return await SessionService(db).set_vote(item_id, user_id, qty, 4)

    # Together they ask for 9 units of a 4-unit dish.
    await asyncio.gather(claim(300, 3), claim(301, 3), claim(302, 3))

    assert await _total_claimed(pg_sessionmaker, item_id) <= 4


async def test_claim_settlement_is_won_by_exactly_one_caller(pg_sessionmaker):
    """Two admins tapping "settle" together must not both notify the table.

    claim_settlement() is a conditional UPDATE, so the database picks the winner. Only
    that caller sends the push notifications; the rest return the same figures quietly.
    """
    async with pg_sessionmaker() as db:
        session = await SessionService(db).create_session(1, "Admin")
        session_id = session.id

    async def settle():
        async with pg_sessionmaker() as db:
            return await SessionService(db).claim_settlement(session_id)

    claims = await asyncio.gather(*(settle() for _ in range(8)))

    assert sum(claims) == 1, f"{sum(claims)} callers believed they settled the session"

    async with pg_sessionmaker() as db:
        from bot.models.session import Session

        settled = await db.get(Session, session_id)
        assert settled.status == "settled"
        assert settled.closed_at is not None


async def test_split_equal_does_not_race_against_a_late_voter(pg_sessionmaker):
    """Admin resolves unclaimed units while someone is still tapping the same dish."""
    session, item_id = await _dish(pg_sessionmaker, quantity=4)

    async def split():
        async with pg_sessionmaker() as db:
            item = await db.get(SessionItem, item_id)
            return await SessionService(db).split_remaining_equally(item, [400, 401])

    async def late_tap():
        async with pg_sessionmaker() as db:
            return await SessionService(db).cycle_vote(item_id, 402, 4)

    await asyncio.gather(split(), late_tap())

    assert await _total_claimed(pg_sessionmaker, item_id) <= 4
    assert session is not None
