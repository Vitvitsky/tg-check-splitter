"""The frontend uses BrowserRouter, so its routes must survive a reload.

StaticFiles(html=True) mounted at "/" only serves index.html for directory paths and
404s on everything else, which made every in-app URL a dead link on refresh or deep
entry. These tests pin the fallback behaviour.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def spa_client(tmp_path, test_settings, monkeypatch):
    """A client whose app serves a throwaway webapp/dist."""
    from unittest.mock import patch

    import httpx

    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>SPA</html>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    (dist / "favicon.ico").write_text("icon")

    import api.app as api_app

    monkeypatch.setattr(api_app, "WEBAPP_DIST", dist)

    with (
        patch("bot.config.get_settings", return_value=test_settings),
        patch("api.auth.get_settings", return_value=test_settings),
    ):
        app = api_app.create_app()
        transport = httpx.ASGITransport(app=app)
        yield httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.parametrize(
    "path",
    ["/", "/scan", "/quota", "/session/abc123", "/session/abc123/vote", "/session/abc123/settle"],
)
async def test_client_routes_serve_the_spa(spa_client, path):
    async with spa_client as client:
        response = await client.get(path)
    assert response.status_code == 200
    assert "SPA" in response.text


async def test_real_files_are_served_as_themselves(spa_client):
    async with spa_client as client:
        asset = await client.get("/assets/app.js")
        favicon = await client.get("/favicon.ico")
    assert asset.status_code == 200 and "console.log" in asset.text
    assert favicon.status_code == 200 and favicon.text == "icon"


async def test_api_routes_are_not_swallowed_by_the_fallback(spa_client):
    """An unknown /api path must stay a 404, not silently become an HTML page."""
    async with spa_client as client:
        health = await client.get("/api/health")
        missing = await client.get("/api/does-not-exist")
    assert health.status_code == 200 and health.json() == {"status": "ok"}
    assert missing.status_code == 404
    assert "SPA" not in missing.text


async def test_path_traversal_is_refused(spa_client):
    """A traversal attempt falls back to index.html rather than leaking a file."""
    async with spa_client as client:
        response = await client.get("/../../etc/passwd")
    assert response.status_code == 200
    assert "root:" not in response.text
