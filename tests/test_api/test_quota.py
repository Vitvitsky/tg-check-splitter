"""Tests for GET /api/quota endpoint."""

import pytest


@pytest.mark.asyncio
async def test_get_quota(client, auth_headers):
    """GET /api/quota with valid auth returns 200 and QuotaOut fields."""
    response = await client.get("/api/quota", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "free_scans_left" in data
    assert "paid_scans" in data
    assert "reset_at" in data

    # Default test settings: free_scans_per_month=3, fresh user has 0 used
    assert data["free_scans_left"] == 3
    assert data["paid_scans"] == 0


@pytest.mark.asyncio
async def test_get_quota_no_auth(client):
    """GET /api/quota without Authorization header returns 401."""
    response = await client.get("/api/quota")
    assert response.status_code == 401
