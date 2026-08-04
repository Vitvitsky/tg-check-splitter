"""Quota endpoint surface.

There used to be a POST /api/quota/reset that zeroed the caller's free-scan counter
with no authorization check at all — the paid tier was one curl away from free. It is
gone, and buying scans now goes through a server-priced Stars invoice.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


async def test_quota_reset_endpoint_no_longer_exists(client, auth_headers):
    response = await client.post("/api/quota/reset", headers=auth_headers)
    assert response.status_code in (404, 405)


async def test_invoice_requires_a_known_pack(client, auth_headers):
    response = await client.post("/api/quota/invoice", json={"scans": 999}, headers=auth_headers)
    assert response.status_code == 400


async def test_invoice_price_comes_from_the_server(client, auth_headers):
    """The client names the pack; the server names the price."""
    mock = AsyncMock(return_value="https://t.me/invoice/xyz")
    with patch("api.routes.quota.NotificationService.create_invoice_link", mock):
        response = await client.post("/api/quota/invoice", json={"scans": 5}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"invoice_link": "https://t.me/invoice/xyz"}
    assert mock.await_args.kwargs["stars"] == 50
    assert mock.await_args.kwargs["payload"] == "scans:5"


async def test_invoice_requires_auth(client):
    response = await client.post("/api/quota/invoice", json={"scans": 5})
    assert response.status_code == 401
