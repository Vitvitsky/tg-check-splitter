"""Query-count guards for the endpoints that used to scale with the data.

Timing tests are flaky and hide regressions on small fixtures; counting statements does
not. `GET /api/sessions/my` issued 5n+1 queries — one per membership, plus the three
lazy="selectin" loads every session carries — measured at 251 queries for 50 sessions.
A single missing eager-load or a reintroduced loop would put that straight back.
"""

from __future__ import annotations

import pytest
from sqlalchemy import event, select

from bot.models.session import Session, SessionItem, SessionMember
from bot.services.session import SessionService
from tests.test_api.conftest import make_init_data

USER = 12345


@pytest.fixture
def count_queries(db_session):
    """Count SQL statements issued on the test engine while inside the block."""
    engine = db_session.get_bind().engine
    counter = {"n": 0}

    def listener(*_args, **_kwargs):
        counter["n"] += 1

    class Counter:
        def __enter__(self):
            counter["n"] = 0
            event.listen(engine, "before_cursor_execute", listener)
            return counter

        def __exit__(self, *_exc):
            event.remove(engine, "before_cursor_execute", listener)

    return Counter


async def _seed(db_session, n_sessions: int, items_per_session: int = 10):
    svc = SessionService(db_session)
    for _ in range(n_sessions):
        session = await svc.create_session(USER, "Owner")
        await svc.save_ocr_items(
            session.id,
            [
                {"name": f"Item{i}", "price": 100 + i, "quantity": 1}
                for i in range(items_per_session)
            ],
        )
        for guest in range(3):
            await svc.join_session(session.invite_code, USER * 100 + guest, f"G{guest}")


@pytest.mark.parametrize("n_sessions", [1, 5, 20])
async def test_my_sessions_cost_does_not_grow_with_the_number_of_sessions(
    client, auth_headers, db_session, count_queries, n_sessions
):
    await _seed(db_session, n_sessions)

    with count_queries() as counter:
        resp = await client.get("/api/sessions/my", headers=auth_headers)

    assert resp.status_code == 200
    assert len(resp.json()) == n_sessions
    assert counter["n"] == 1, f"{counter['n']} queries for {n_sessions} sessions — the N+1 is back"


async def test_my_sessions_still_reports_the_right_counts(client, auth_headers, db_session):
    """Counts moved from len(relationship) into SQL — they must still be correct."""
    await _seed(db_session, n_sessions=1, items_per_session=7)

    resp = await client.get("/api/sessions/my", headers=auth_headers)

    brief = resp.json()[0]
    assert brief["item_count"] == 7
    assert brief["member_count"] == 4, "admin + three guests"


async def test_clear_history_is_a_single_statement(
    client, auth_headers, db_session, count_queries
):
    await _seed(db_session, n_sessions=5)
    await db_session.execute(
        Session.__table__.update().where(Session.admin_tg_id == USER).values(status="settled")
    )
    await db_session.commit()

    with count_queries() as counter:
        resp = await client.request("DELETE", "/api/sessions/history", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["deleted"] == 5
    # One DELETE ... RETURNING, plus the transaction's COMMIT.
    assert counter["n"] <= 2, f"{counter['n']} queries — clear_history is looping again"

    left = await db_session.execute(select(Session).where(Session.admin_tg_id == USER))
    assert left.scalars().all() == []


async def test_clear_history_leaves_other_peoples_sessions_alone(client, db_session):
    """The bulk DELETE must stay scoped to the caller's own settled sessions."""
    svc = SessionService(db_session)
    mine = await svc.create_session(USER, "Me")
    theirs = await svc.create_session(999, "Someone else")
    await db_session.execute(Session.__table__.update().values(status="settled"))
    await db_session.commit()

    headers = {"Authorization": f"tma {make_init_data(user_id=USER)}"}
    resp = await client.request("DELETE", "/api/sessions/history", headers=headers)

    assert resp.json()["deleted"] == 1
    remaining = (await db_session.execute(select(Session.id))).scalars().all()
    assert remaining == [theirs.id]
    assert mine.id not in remaining


async def test_unsettled_sessions_are_not_deleted(client, auth_headers, db_session):
    await _seed(db_session, n_sessions=2)

    resp = await client.request("DELETE", "/api/sessions/history", headers=auth_headers)

    assert resp.json()["deleted"] == 0
    rows = await db_session.execute(select(SessionMember).where(SessionMember.user_tg_id == USER))
    assert len(rows.scalars().all()) == 2


async def test_items_are_removed_with_the_session(client, auth_headers, db_session):
    """clear_history relies on ON DELETE CASCADE now that it no longer loads children."""
    await _seed(db_session, n_sessions=1, items_per_session=4)
    await db_session.execute(
        Session.__table__.update().where(Session.admin_tg_id == USER).values(status="settled")
    )
    await db_session.commit()

    await client.request("DELETE", "/api/sessions/history", headers=auth_headers)

    items = await db_session.execute(select(SessionItem))
    assert items.scalars().all() == []
