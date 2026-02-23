"""Tests for session CRUD REST routes."""

from __future__ import annotations

import pytest

from bot.services.session import SessionService
from tests.test_api.conftest import make_init_data


@pytest.mark.asyncio
async def test_create_session(client, auth_headers):
    """POST /api/sessions -> 201 with a new session."""
    resp = await client.post(
        "/api/sessions",
        json={"currency": "USD"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["currency"] == "USD"
    assert data["status"] == "created"
    assert data["admin_tg_id"] == 12345
    assert len(data["members"]) == 1
    assert data["members"][0]["user_tg_id"] == 12345


@pytest.mark.asyncio
async def test_get_session_by_invite(client, auth_headers):
    """GET /api/sessions/invite/{code} -> 200 with the session."""
    # Create a session first
    create_resp = await client.post(
        "/api/sessions",
        json={"currency": "RUB"},
        headers=auth_headers,
    )
    invite_code = create_resp.json()["invite_code"]

    resp = await client.get(
        f"/api/sessions/invite/{invite_code}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["invite_code"] == invite_code


@pytest.mark.asyncio
async def test_get_session_not_found(client, auth_headers):
    """GET /api/sessions/{bad_id} -> 404."""
    import uuid

    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/sessions/{fake_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_join_session(client, auth_headers):
    """POST /api/sessions/invite/{code}/join -> 201 for a new user."""
    # Create session as default user (12345)
    create_resp = await client.post(
        "/api/sessions",
        json={"currency": "RUB"},
        headers=auth_headers,
    )
    invite_code = create_resp.json()["invite_code"]

    # Join as a different user
    second_user_init_data = make_init_data(user_id=99999, first_name="Alice")
    second_headers = {"Authorization": f"tma {second_user_init_data}"}

    resp = await client.post(
        f"/api/sessions/invite/{invite_code}/join",
        headers=second_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_tg_id"] == 99999
    assert data["display_name"] == "Alice"


@pytest.mark.asyncio
async def test_join_session_already_member(client, auth_headers):
    """POST /api/sessions/invite/{code}/join -> 409 when already a member."""
    create_resp = await client.post(
        "/api/sessions",
        json={"currency": "RUB"},
        headers=auth_headers,
    )
    invite_code = create_resp.json()["invite_code"]

    # The admin (default user 12345) is already a member
    resp = await client.post(
        f"/api/sessions/invite/{invite_code}/join",
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_my_sessions(client, auth_headers):
    """GET /api/sessions/my -> list of session briefs."""
    # Create two sessions
    await client.post(
        "/api/sessions",
        json={"currency": "RUB"},
        headers=auth_headers,
    )
    await client.post(
        "/api/sessions",
        json={"currency": "USD"},
        headers=auth_headers,
    )

    resp = await client.get("/api/sessions/my", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Each brief has the expected fields
    for brief in data:
        assert "id" in brief
        assert "invite_code" in brief
        assert "status" in brief
        assert "member_count" in brief
        assert "item_count" in brief


@pytest.mark.asyncio
async def test_finish_not_admin(client, auth_headers):
    """POST /api/sessions/{id}/finish -> 403 when not admin."""
    create_resp = await client.post(
        "/api/sessions",
        json={"currency": "RUB"},
        headers=auth_headers,
    )
    session_id = create_resp.json()["id"]
    invite_code = create_resp.json()["invite_code"]

    # Join as a different user
    second_user_init_data = make_init_data(user_id=99999, first_name="Alice")
    second_headers = {"Authorization": f"tma {second_user_init_data}"}
    await client.post(
        f"/api/sessions/invite/{invite_code}/join",
        headers=second_headers,
    )

    # Non-admin tries to finish
    resp = await client.post(
        f"/api/sessions/{session_id}/finish",
        headers=second_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_settle(client, auth_headers, db_session):
    """POST /api/sessions/{id}/settle -> calculates shares."""
    # Create session
    create_resp = await client.post(
        "/api/sessions",
        json={"currency": "RUB"},
        headers=auth_headers,
    )
    session_data = create_resp.json()
    session_id = session_data["id"]
    invite_code = session_data["invite_code"]

    # Join as second user
    second_user_init_data = make_init_data(user_id=99999, first_name="Alice")
    second_headers = {"Authorization": f"tma {second_user_init_data}"}
    await client.post(
        f"/api/sessions/invite/{invite_code}/join",
        headers=second_headers,
    )

    # Add items directly via the service (simulating OCR)
    svc = SessionService(db_session)
    items = await svc.save_ocr_items(session_id, [
        {"name": "Pizza", "price": 1000, "quantity": 2},
        {"name": "Beer", "price": 300, "quantity": 1},
    ])

    # User 12345 claims 1 pizza, user 99999 claims 1 pizza + 1 beer
    pizza = next(i for i in items if i.name == "Pizza")
    beer = next(i for i in items if i.name == "Beer")

    await svc.cycle_vote(pizza.id, 12345, pizza.quantity)   # 12345 -> 1 pizza
    await svc.cycle_vote(pizza.id, 99999, pizza.quantity)   # 99999 -> 1 pizza
    await svc.cycle_vote(beer.id, 99999, beer.quantity)     # 99999 -> 1 beer

    # Settle as admin
    resp = await client.post(
        f"/api/sessions/{session_id}/settle",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    shares = resp.json()
    assert len(shares) == 2

    # Check that each share has the right fields
    for share in shares:
        assert "user_tg_id" in share
        assert "display_name" in share
        assert "dishes_total" in share
        assert "tip_amount" in share
        assert "grand_total" in share

    # User 12345: 1 pizza = 500, user 99999: 1 pizza + 1 beer = 500 + 300 = 800
    user_12345 = next(s for s in shares if s["user_tg_id"] == 12345)
    user_99999 = next(s for s in shares if s["user_tg_id"] == 99999)
    assert user_12345["dishes_total"] == 500.0
    assert user_99999["dishes_total"] == 800.0
