"""Tests for voting, tip, confirmation, and share-calculation routes."""

from __future__ import annotations

import pytest

from bot.services.session import SessionService


# ---------------------------------------------------------------------------
# Helper: create a session with items via the DB directly
# ---------------------------------------------------------------------------


@pytest.fixture
async def session_with_items(client, auth_headers, db_session):
    """Create a session via the API, then add items directly via SessionService.

    Returns (session_id, item_ids) where item_ids is a list of item UUID strings.
    """
    # Create session via API (creates admin member with user_tg_id=12345)
    resp = await client.post("/api/sessions", json={}, headers=auth_headers)
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    # Add items via service
    svc = SessionService(db_session)
    items = await svc.save_ocr_items(
        session_id,
        [
            {"name": "Pizza", "price": 500, "quantity": 2},
            {"name": "Beer", "price": 300, "quantity": 1},
            {"name": "Salad", "price": 200, "quantity": 3},
        ],
    )
    item_ids = [str(item.id) for item in items]
    return session_id, item_ids


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVoteCycle:
    """POST /api/sessions/{id}/vote — cycle vote on an item."""

    @pytest.mark.asyncio
    async def test_vote_first_click(self, client, auth_headers, session_with_items):
        session_id, item_ids = session_with_items

        resp = await client.post(
            f"/api/sessions/{session_id}/vote",
            json={"item_id": item_ids[0]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["quantity"] == 1
        assert data["overflow_prevented"] is False

    @pytest.mark.asyncio
    async def test_vote_cycle_increments(self, client, auth_headers, session_with_items):
        """Clicking repeatedly increments quantity up to max, then resets to 0."""
        session_id, item_ids = session_with_items
        pizza_id = item_ids[0]  # quantity=2

        # Vote 1
        resp = await client.post(
            f"/api/sessions/{session_id}/vote",
            json={"item_id": pizza_id},
            headers=auth_headers,
        )
        assert resp.json()["quantity"] == 1

        # Vote 2 (max for this item)
        resp = await client.post(
            f"/api/sessions/{session_id}/vote",
            json={"item_id": pizza_id},
            headers=auth_headers,
        )
        assert resp.json()["quantity"] == 2

        # Vote 3 -> resets to 0
        resp = await client.post(
            f"/api/sessions/{session_id}/vote",
            json={"item_id": pizza_id},
            headers=auth_headers,
        )
        assert resp.json()["quantity"] == 0

    @pytest.mark.asyncio
    async def test_vote_item_not_found(self, client, auth_headers, session_with_items):
        session_id, _ = session_with_items

        resp = await client.post(
            f"/api/sessions/{session_id}/vote",
            json={"item_id": "00000000-0000-0000-0000-000000000000"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_vote_session_not_found(self, client, auth_headers):
        resp = await client.post(
            "/api/sessions/00000000-0000-0000-0000-000000000000/vote",
            json={"item_id": "00000000-0000-0000-0000-000000000000"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestSetTip:
    """POST /api/sessions/{id}/tip — set tip percent."""

    @pytest.mark.asyncio
    async def test_set_tip_success(self, client, auth_headers, session_with_items):
        session_id, _ = session_with_items

        resp = await client.post(
            f"/api/sessions/{session_id}/tip",
            json={"tip_percent": 15},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_set_tip_zero(self, client, auth_headers, session_with_items):
        session_id, _ = session_with_items

        resp = await client.post(
            f"/api/sessions/{session_id}/tip",
            json={"tip_percent": 0},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_set_tip_invalid_negative(self, client, auth_headers, session_with_items):
        session_id, _ = session_with_items

        resp = await client.post(
            f"/api/sessions/{session_id}/tip",
            json={"tip_percent": -5},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_set_tip_invalid_over_100(self, client, auth_headers, session_with_items):
        session_id, _ = session_with_items

        resp = await client.post(
            f"/api/sessions/{session_id}/tip",
            json={"tip_percent": 101},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestConfirm:
    """POST /api/sessions/{id}/confirm and /unconfirm."""

    @pytest.mark.asyncio
    async def test_confirm(self, client, auth_headers, session_with_items):
        session_id, _ = session_with_items

        resp = await client.post(
            f"/api/sessions/{session_id}/confirm",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_unconfirm(self, client, auth_headers, session_with_items):
        session_id, _ = session_with_items

        # Confirm first
        await client.post(
            f"/api/sessions/{session_id}/confirm",
            headers=auth_headers,
        )
        # Then unconfirm
        resp = await client.post(
            f"/api/sessions/{session_id}/unconfirm",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestGetShares:
    """GET /api/sessions/{id}/shares — all shares after voting."""

    @pytest.mark.asyncio
    async def test_get_shares_with_votes(
        self, client, auth_headers, session_with_items
    ):
        session_id, item_ids = session_with_items

        # Vote on Pizza (qty 1 of 2) and Beer (qty 1 of 1)
        await client.post(
            f"/api/sessions/{session_id}/vote",
            json={"item_id": item_ids[0]},
            headers=auth_headers,
        )
        await client.post(
            f"/api/sessions/{session_id}/vote",
            json={"item_id": item_ids[1]},
            headers=auth_headers,
        )

        # Set tip
        await client.post(
            f"/api/sessions/{session_id}/tip",
            json={"tip_percent": 10},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/sessions/{session_id}/shares",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1  # Only one voter

        share = data[0]
        assert share["user_tg_id"] == 12345
        assert share["display_name"] == "Test"
        # Pizza: 500/2 * 1 = 250, Beer: 300 => dishes_total = 550
        assert share["dishes_total"] == 550.0
        # 10% tip: 55.0
        assert share["tip_amount"] == 55.0
        # Grand total (ceil): 605
        assert share["grand_total"] == 605.0

    @pytest.mark.asyncio
    async def test_get_shares_empty_no_votes(
        self, client, auth_headers, session_with_items
    ):
        session_id, _ = session_with_items

        resp = await client.get(
            f"/api/sessions/{session_id}/shares",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetMyShare:
    """GET /api/sessions/{id}/my-share — current user's share breakdown."""

    @pytest.mark.asyncio
    async def test_my_share(self, client, auth_headers, session_with_items):
        session_id, item_ids = session_with_items

        # Vote on Beer (300, qty 1)
        await client.post(
            f"/api/sessions/{session_id}/vote",
            json={"item_id": item_ids[1]},
            headers=auth_headers,
        )

        # Set tip 20%
        await client.post(
            f"/api/sessions/{session_id}/tip",
            json={"tip_percent": 20},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/sessions/{session_id}/my-share",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_tg_id"] == 12345
        assert data["dishes_total"] == 300.0
        assert data["tip_amount"] == 60.0
        assert data["grand_total"] == 360.0

    @pytest.mark.asyncio
    async def test_my_share_no_votes(
        self, client, auth_headers, session_with_items
    ):
        session_id, _ = session_with_items

        resp = await client.get(
            f"/api/sessions/{session_id}/my-share",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dishes_total"] == 0.0
        assert data["tip_amount"] == 0.0
        assert data["grand_total"] == 0.0
