"""Tests for OCR and item management routes."""

from __future__ import annotations

import pytest

from bot.services.session import SessionService
from tests.test_api.conftest import make_init_data


@pytest.fixture
async def session_id(db_session, auth_headers):
    """Create a session owned by the default test user (id=12345)."""
    svc = SessionService(db_session)
    session = await svc.create_session(admin_tg_id=12345, admin_display_name="Test")
    return str(session.id)


@pytest.fixture
def other_auth_headers():
    """Authorization headers for a different user (id=99999)."""
    init_data = make_init_data(user_id=99999, first_name="Other")
    return {"Authorization": f"tma {init_data}"}


# ---- PUT /api/sessions/{session_id}/items (replace all) ----


@pytest.mark.asyncio
async def test_update_items(client, auth_headers, session_id):
    """PUT items replaces all items and returns the new list."""
    payload = {
        "items": [
            {"name": "Pizza", "price": 500.0, "quantity": 1},
            {"name": "Beer", "price": 300.0, "quantity": 2},
        ]
    }
    resp = await client.put(
        f"/api/sessions/{session_id}/items",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "Pizza"
    assert data[0]["price"] == 500.0
    assert data[0]["quantity"] == 1
    assert data[1]["name"] == "Beer"
    assert data[1]["price"] == 300.0
    assert data[1]["quantity"] == 2
    # Each item must have an id
    assert data[0]["id"]
    assert data[1]["id"]


@pytest.mark.asyncio
async def test_update_items_replaces_old(client, auth_headers, session_id):
    """PUT items twice — second call replaces the first batch entirely."""
    first = {"items": [{"name": "Old", "price": 100.0, "quantity": 1}]}
    await client.put(f"/api/sessions/{session_id}/items", json=first, headers=auth_headers)

    second = {"items": [{"name": "New", "price": 200.0, "quantity": 3}]}
    resp = await client.put(f"/api/sessions/{session_id}/items", json=second, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "New"


@pytest.mark.asyncio
async def test_update_items_not_admin(client, other_auth_headers, session_id):
    """PUT items by a non-admin returns 403."""
    payload = {"items": [{"name": "Pizza", "price": 500.0, "quantity": 1}]}
    resp = await client.put(
        f"/api/sessions/{session_id}/items",
        json=payload,
        headers=other_auth_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_items_session_not_found(client, auth_headers):
    """PUT items for a non-existent session returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    payload = {"items": [{"name": "X", "price": 1.0, "quantity": 1}]}
    resp = await client.put(
        f"/api/sessions/{fake_id}/items",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ---- PUT /api/sessions/{session_id}/items/{item_id} (update single) ----


@pytest.mark.asyncio
async def test_update_single_item(client, auth_headers, session_id):
    """PUT single item updates name and price."""
    # Create items first
    payload = {"items": [{"name": "Steak", "price": 1000.0, "quantity": 1}]}
    create_resp = await client.put(
        f"/api/sessions/{session_id}/items", json=payload, headers=auth_headers
    )
    item_id = create_resp.json()[0]["id"]

    # Update it
    resp = await client.put(
        f"/api/sessions/{session_id}/items/{item_id}",
        json={"name": "Ribeye Steak", "price": 1200.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_single_item_not_admin(client, other_auth_headers, auth_headers, session_id):
    """PUT single item by non-admin returns 403."""
    payload = {"items": [{"name": "Steak", "price": 1000.0, "quantity": 1}]}
    create_resp = await client.put(
        f"/api/sessions/{session_id}/items", json=payload, headers=auth_headers
    )
    item_id = create_resp.json()[0]["id"]

    resp = await client.put(
        f"/api/sessions/{session_id}/items/{item_id}",
        json={"name": "Hacked", "price": 0.01},
        headers=other_auth_headers,
    )
    assert resp.status_code == 403


# ---- DELETE /api/sessions/{session_id}/items/{item_id} ----


@pytest.mark.asyncio
async def test_delete_item(client, auth_headers, session_id):
    """DELETE item returns 204 and removes the item."""
    payload = {
        "items": [
            {"name": "A", "price": 100.0, "quantity": 1},
            {"name": "B", "price": 200.0, "quantity": 1},
        ]
    }
    create_resp = await client.put(
        f"/api/sessions/{session_id}/items", json=payload, headers=auth_headers
    )
    items = create_resp.json()
    item_to_delete = items[0]["id"]

    resp = await client.delete(
        f"/api/sessions/{session_id}/items/{item_to_delete}",
        headers=auth_headers,
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_item_not_admin(client, other_auth_headers, auth_headers, session_id):
    """DELETE item by non-admin returns 403."""
    payload = {"items": [{"name": "A", "price": 100.0, "quantity": 1}]}
    create_resp = await client.put(
        f"/api/sessions/{session_id}/items", json=payload, headers=auth_headers
    )
    item_id = create_resp.json()[0]["id"]

    resp = await client.delete(
        f"/api/sessions/{session_id}/items/{item_id}",
        headers=other_auth_headers,
    )
    assert resp.status_code == 403


# ---- POST /api/sessions/{session_id}/photos ----


@pytest.mark.asyncio
async def test_upload_photos(client, auth_headers, session_id):
    """POST photos uploads files and returns PhotoOut list."""
    fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # minimal fake image bytes
    resp = await client.post(
        f"/api/sessions/{session_id}/photos",
        headers=auth_headers,
        files=[("files", ("receipt.png", fake_image, "image/png"))],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 1
    assert data[0]["tg_file_id"].startswith("miniapp-")
    assert data[0]["id"]


@pytest.mark.asyncio
async def test_upload_photos_not_admin(client, other_auth_headers, session_id):
    """POST photos by non-admin returns 403."""
    fake_image = b"\x89PNG" + b"\x00" * 100
    resp = await client.post(
        f"/api/sessions/{session_id}/photos",
        headers=other_auth_headers,
        files=[("files", ("receipt.png", fake_image, "image/png"))],
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_upload_photos_too_large(client, auth_headers, session_id):
    """POST photo exceeding 5 MB returns 413."""
    big_data = b"\x00" * (5 * 1024 * 1024 + 1)
    resp = await client.post(
        f"/api/sessions/{session_id}/photos",
        headers=auth_headers,
        files=[("files", ("big.png", big_data, "image/png"))],
    )
    assert resp.status_code == 413
