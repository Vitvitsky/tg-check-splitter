"""Smoke tests for the /api/health endpoint and fixture wiring."""

import pytest


@pytest.mark.asyncio
async def test_health(client):
    """GET /api/health returns 200 with {"status": "ok"}."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
