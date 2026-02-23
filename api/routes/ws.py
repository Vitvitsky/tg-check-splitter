"""WebSocket endpoint for real-time session updates."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from api.auth import _parse_telegram_user, validate_init_data
from bot.config import get_settings
from bot.db import get_async_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
):
    """WebSocket endpoint for real-time session updates.

    Auth via query param: /ws/{session_id}?token=<initData>
    """
    # Validate auth
    try:
        settings = get_settings()
        params = validate_init_data(token, settings.bot_token)
    except (ValueError, Exception):
        await websocket.close(code=4001, reason="Invalid authentication")
        return

    user = _parse_telegram_user(params.get("user", "{}"))

    # Verify user is a member of the session
    async_session_factory = get_async_session()
    async with async_session_factory() as db:
        from bot.services.session import SessionService

        svc = SessionService(db)
        member = await svc.get_member(session_id, user.id)
        if member is None:
            await websocket.close(code=4003, reason="Not a session member")
            return

    # Connect to the manager
    manager = websocket.app.state.ws_manager
    await manager.connect(session_id, websocket)

    try:
        while True:
            # Keep connection alive; receive messages (ping/pong handled by protocol)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
    except Exception:
        manager.disconnect(session_id, websocket)
