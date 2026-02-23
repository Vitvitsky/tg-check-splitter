from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from api.ws import ConnectionManager


@pytest.mark.asyncio
async def test_connect_adds_to_connections():
    mgr = ConnectionManager()
    ws = AsyncMock()
    await mgr.connect("session-1", ws)
    assert mgr.get_connection_count("session-1") == 1
    ws.accept.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnect_removes():
    mgr = ConnectionManager()
    ws = AsyncMock()
    await mgr.connect("session-1", ws)
    mgr.disconnect("session-1", ws)
    assert mgr.get_connection_count("session-1") == 0


@pytest.mark.asyncio
async def test_disconnect_cleans_empty_session():
    mgr = ConnectionManager()
    ws = AsyncMock()
    await mgr.connect("session-1", ws)
    mgr.disconnect("session-1", ws)
    assert "session-1" not in mgr._connections


@pytest.mark.asyncio
async def test_broadcast_sends_to_all():
    mgr = ConnectionManager()
    ws1, ws2 = AsyncMock(), AsyncMock()
    await mgr.connect("s1", ws1)
    await mgr.connect("s1", ws2)
    event = {"type": "vote_updated", "data": {"item_id": "123"}}
    await mgr.broadcast("s1", event)
    ws1.send_json.assert_awaited_once_with(event)
    ws2.send_json.assert_awaited_once_with(event)


@pytest.mark.asyncio
async def test_broadcast_handles_disconnected_client():
    mgr = ConnectionManager()
    ws_good = AsyncMock()
    ws_bad = AsyncMock()
    ws_bad.send_json.side_effect = RuntimeError("connection closed")
    await mgr.connect("s1", ws_good)
    await mgr.connect("s1", ws_bad)
    await mgr.broadcast("s1", {"type": "test"})
    # Bad ws should be disconnected
    assert mgr.get_connection_count("s1") == 1


@pytest.mark.asyncio
async def test_broadcast_to_empty_session():
    mgr = ConnectionManager()
    # Should not raise
    await mgr.broadcast("nonexistent", {"type": "test"})


@pytest.mark.asyncio
async def test_ws_manager_initialized(test_settings):
    """Verify ws_manager is available on app state after create_app."""
    with (
        patch("bot.config.get_settings", return_value=test_settings),
        patch("api.auth.get_settings", return_value=test_settings),
    ):
        from api.app import create_app

        app = create_app()
        assert hasattr(app.state, "ws_manager")
        assert isinstance(app.state.ws_manager, ConnectionManager)
