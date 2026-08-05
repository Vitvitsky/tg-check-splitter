"""Regression tests for splitting unclaimed items.

The previous implementation computed ``max(1, remaining // len(members))`` and then
added a remainder on top, so one unclaimed unit split across three members handed out
four units — the table was billed more than the receipt said.
"""

import pytest

from core.services.session import SessionService


async def _item(db, *, quantity: int, price=900):
    svc = SessionService(db)
    session = await svc.create_session(1, "Admin")
    items = await svc.save_ocr_items(
        session.id, [{"name": "Pizza", "price": price, "quantity": quantity}]
    )
    return svc, items[0]


async def _claims(db, svc, item) -> dict[int, int]:
    await db.refresh(item, ["votes"])
    return {v.user_tg_id: v.quantity for v in item.votes}


@pytest.mark.parametrize(
    ("quantity", "members"),
    [(1, 3), (2, 3), (3, 3), (4, 3), (6, 3), (5, 2), (1, 1), (7, 4)],
)
async def test_split_hands_out_exactly_the_unclaimed_units(db_session, quantity, members):
    svc, item = await _item(db_session, quantity=quantity)
    member_ids = list(range(100, 100 + members))

    handed_out = await svc.split_remaining_equally(item, member_ids)

    claims = await _claims(db_session, svc, item)
    assert handed_out == quantity
    assert sum(claims.values()) == quantity, "must never claim more units than the dish has"


async def test_split_only_distributes_what_is_left(db_session):
    """Units already claimed by a member stay theirs and are not redistributed."""
    svc, item = await _item(db_session, quantity=5)
    await svc.set_vote(item.id, 100, 3, item.quantity)

    handed_out = await svc.split_remaining_equally(item, [100, 200])

    claims = await _claims(db_session, svc, item)
    assert handed_out == 2
    assert claims[100] == 3 + 1, "existing claim must be added to, not overwritten"
    assert claims[200] == 1
    assert sum(claims.values()) == 5


async def test_split_favours_the_least_claimed_member(db_session):
    """With fewer units than members the leftovers go to whoever has taken the least."""
    svc, item = await _item(db_session, quantity=4)
    await svc.set_vote(item.id, 100, 3, item.quantity)

    await svc.split_remaining_equally(item, [100, 200, 300])

    claims = await _claims(db_session, svc, item)
    assert claims.get(200) == 1
    assert claims.get(300) is None
    assert claims[100] == 3


async def test_split_on_a_fully_claimed_item_is_a_no_op(db_session):
    svc, item = await _item(db_session, quantity=2)
    await svc.set_vote(item.id, 100, 2, item.quantity)

    assert await svc.split_remaining_equally(item, [100, 200]) == 0
    assert await _claims(db_session, svc, item) == {100: 2}
