"""Settlement happens once, and its numbers stop moving afterwards.

`POST /settle` used to recompute and re-notify on every call: a double tap, a retry
after a dropped connection, or a refetch told every participant their total again.
Worse, nothing stopped voting *after* settlement — and shares are computed on read, so
the figure on screen would quietly drift away from the one in the push notification.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from core.models.session import Session
from core.services.session import SessionService
from tests.test_api.conftest import make_init_data

ADMIN = 12345
GUEST = 54321


@pytest.fixture
async def settled_ready(client, db_session):
    """A session with two members, one dish each, ready to be settled."""
    svc = SessionService(db_session)
    session = await svc.create_session(ADMIN, "Admin")
    items = await svc.save_ocr_items(
        session.id,
        [
            {"name": "Pizza", "price": 600, "quantity": 1},
            {"name": "Beer", "price": 400, "quantity": 1},
        ],
    )
    await svc.join_session(session.invite_code, GUEST, "Guest")
    await svc.set_vote(items[0].id, ADMIN, 1, 1)
    await svc.set_vote(items[1].id, GUEST, 1, 1)
    return session, items


@pytest.fixture
def guest_headers():
    return {"Authorization": f"tma {make_init_data(user_id=GUEST, first_name='Guest')}"}


async def test_settling_twice_returns_the_same_numbers(
    client, auth_headers, settled_ready, db_session
):
    session, _items = settled_ready

    first = await client.post(f"/api/sessions/{session.id}/settle", headers=auth_headers)
    second = await client.post(f"/api/sessions/{session.id}/settle", headers=auth_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert sorted(first.json(), key=lambda s: s["user_tg_id"]) == sorted(
        second.json(), key=lambda s: s["user_tg_id"]
    )


async def test_only_the_first_settlement_notifies(client, auth_headers, settled_ready):
    """The whole point: nobody is told their total twice."""
    session, _items = settled_ready

    # conftest patches api.routes.sessions.NotificationService with a single AsyncMock,
    # so every construction inside the route returns the same object to count on.
    from api.routes import sessions as sessions_module

    mock = sessions_module.NotificationService.return_value

    await client.post(f"/api/sessions/{session.id}/settle", headers=auth_headers)
    assert mock.notify_settle.await_count == 1

    await client.post(f"/api/sessions/{session.id}/settle", headers=auth_headers)
    await client.post(f"/api/sessions/{session.id}/settle", headers=auth_headers)
    assert mock.notify_settle.await_count == 1, "retries re-notified every participant"


async def test_settlement_records_when_it_closed(client, auth_headers, settled_ready, db_session):
    """closed_at existed on the model and was never written."""
    session, _items = settled_ready

    await client.post(f"/api/sessions/{session.id}/settle", headers=auth_headers)

    row = await db_session.execute(select(Session).where(Session.id == session.id))
    settled = row.scalar_one()
    await db_session.refresh(settled)
    assert settled.status == "settled"
    assert settled.closed_at is not None


# ---------------------------------------------------------------------------
# A settled session is frozen — that is what keeps the numbers stable
# ---------------------------------------------------------------------------


async def test_voting_is_refused_after_settlement(
    client, auth_headers, guest_headers, settled_ready
):
    session, items = settled_ready
    await client.post(f"/api/sessions/{session.id}/settle", headers=auth_headers)

    resp = await client.post(
        f"/api/sessions/{session.id}/vote",
        json={"item_id": str(items[0].id), "quantity": 1},
        headers=guest_headers,
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == "session_settled"


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("tip", {"tip_percent": 20}),
        ("confirm", None),
        ("unconfirm", None),
    ],
)
async def test_participant_changes_are_refused_after_settlement(
    client, auth_headers, guest_headers, settled_ready, path, payload
):
    session, _items = settled_ready
    await client.post(f"/api/sessions/{session.id}/settle", headers=auth_headers)

    resp = await client.post(
        f"/api/sessions/{session.id}/{path}", json=payload, headers=guest_headers
    )

    assert resp.status_code == 409


async def test_editing_the_receipt_is_refused_after_settlement(
    client, auth_headers, settled_ready
):
    session, items = settled_ready
    await client.post(f"/api/sessions/{session.id}/settle", headers=auth_headers)

    replace = await client.put(
        f"/api/sessions/{session.id}/items",
        json={"items": [{"name": "Sneaky", "price": 1.0, "quantity": 1}]},
        headers=auth_headers,
    )
    delete = await client.delete(
        f"/api/sessions/{session.id}/items/{items[0].id}", headers=auth_headers
    )

    assert replace.status_code == 409
    assert delete.status_code == 409


async def test_a_tip_change_cannot_move_a_settled_total(
    client, auth_headers, guest_headers, settled_ready
):
    """The regression that made retries dangerous: shares are computed on read."""
    session, _items = settled_ready

    first = await client.post(f"/api/sessions/{session.id}/settle", headers=auth_headers)
    before = {s["user_tg_id"]: s["grand_total"] for s in first.json()}

    # Guest tries to add a 50% tip after being told what they owe.
    blocked = await client.post(
        f"/api/sessions/{session.id}/tip", json={"tip_percent": 50}, headers=guest_headers
    )
    assert blocked.status_code == 409

    shares = await client.get(f"/api/sessions/{session.id}/shares", headers=auth_headers)
    after = {s["user_tg_id"]: s["grand_total"] for s in shares.json()}
    assert after == before


async def test_shares_stay_readable_after_settlement(client, auth_headers, settled_ready):
    """Freezing must not lock participants out of seeing their own total."""
    session, _items = settled_ready
    await client.post(f"/api/sessions/{session.id}/settle", headers=auth_headers)

    shares = await client.get(f"/api/sessions/{session.id}/shares", headers=auth_headers)
    mine = await client.get(f"/api/sessions/{session.id}/my-share", headers=auth_headers)

    assert shares.status_code == 200
    assert mine.status_code == 200
    assert mine.json()["grand_total"] == Decimal("600")


# Genuinely concurrent settles need one DB session per caller and a database that
# actually isolates them — see test_claim_settlement_is_won_by_exactly_one_caller in
# tests/test_concurrency.py. This suite shares a single AsyncSession across requests,
# so firing them together here would only reproduce SQLAlchemy's own
# IllegalStateChangeError, not the race being guarded against.
