"""Regression tests for data-integrity bugs that shipped with a green test suite.

Every case here failed before the f1a2b3c4d5e6 migration. They only fail against a
database that actually enforces foreign keys and unique constraints — see tests/db.py
for why that was not the case before.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.models.session import ItemVote, SessionItem, SessionMember
from core.services.session import SessionService


async def _session_with_item(db, *, admin=1, name="Pizza", price=900, quantity=3):
    svc = SessionService(db)
    session = await svc.create_session(admin, "Admin")
    items = await svc.save_ocr_items(
        session.id, [{"name": name, "price": price, "quantity": quantity}]
    )
    return svc, session, items[0]


# ---------------------------------------------------------------------------
# Cascades
# ---------------------------------------------------------------------------


async def test_delete_item_with_votes_removes_its_votes(db_session):
    """Deleting a voted-on item used to raise IntegrityError (no ON DELETE rule)."""
    svc, _session, item = await _session_with_item(db_session)
    await svc.cycle_vote(item.id, 1, item.quantity)

    await svc.delete_item(item.id)

    votes = await db_session.execute(select(ItemVote).where(ItemVote.item_id == item.id))
    assert votes.scalars().all() == []


async def test_delete_session_cascades_to_all_children(db_session):
    """`DELETE /api/sessions/history` failed 100% of the time before this."""
    svc, session, item = await _session_with_item(db_session)
    await svc.add_photo(session.id, "file-1")
    await svc.cycle_vote(item.id, 1, item.quantity)

    await db_session.delete(session)
    await db_session.commit()

    for model, column in (
        (SessionItem, SessionItem.session_id),
        (SessionMember, SessionMember.session_id),
    ):
        rows = await db_session.execute(select(model).where(column == session.id))
        assert rows.scalars().all() == [], f"{model.__name__} outlived its session"

    votes = await db_session.execute(select(ItemVote).where(ItemVote.item_id == item.id))
    assert votes.scalars().all() == []


# ---------------------------------------------------------------------------
# Uniqueness
# ---------------------------------------------------------------------------


async def test_duplicate_membership_is_rejected(db_session):
    """A second membership row wedged get_member() with MultipleResultsFound forever."""
    svc, session, _item = await _session_with_item(db_session)
    # Hold the id: the rollback below expires `session`, and refreshing an expired
    # attribute mid-test would fail for reasons unrelated to what is being asserted.
    session_id = session.id
    db_session.add(SessionMember(session_id=session_id, user_tg_id=42, display_name="A"))
    await db_session.commit()

    db_session.add(SessionMember(session_id=session_id, user_tg_id=42, display_name="B"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    assert (await svc.get_member(session_id, 42)) is not None


async def test_concurrent_join_returns_none_instead_of_raising(db_session):
    """join_session() must absorb the unique-constraint loss, not 500."""
    svc, session, _item = await _session_with_item(db_session)
    first = await svc.join_session(session.invite_code, 77, "Guest")
    assert first is not None

    assert await svc.join_session(session.invite_code, 77, "Guest") is None


async def test_duplicate_vote_row_is_rejected(db_session):
    """A double tap used to insert a second vote and break cycle_vote() permanently."""
    _svc, _session, item = await _session_with_item(db_session)
    db_session.add(ItemVote(item_id=item.id, user_tg_id=7, quantity=1))
    await db_session.commit()

    db_session.add(ItemVote(item_id=item.id, user_tg_id=7, quantity=1))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_cycle_vote_still_works_after_a_lost_race(db_session):
    """The IntegrityError path must report the row that actually landed."""
    svc, _session, item = await _session_with_item(db_session)
    db_session.add(ItemVote(item_id=item.id, user_tg_id=9, quantity=2))
    await db_session.commit()
    db_session.expunge_all()

    quantity, overflow = await svc.cycle_vote(item.id, 9, item.quantity)
    assert (quantity, overflow) == (3, False)
