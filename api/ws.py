"""WebSocket connection manager for real-time session updates."""

from __future__ import annotations

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Event type constants
EVENT_VOTE_UPDATED = "vote_updated"
EVENT_MEMBER_JOINED = "member_joined"
EVENT_MEMBER_CONFIRMED = "member_confirmed"
EVENT_MEMBER_UNCONFIRMED = "member_unconfirmed"
EVENT_TIP_CHANGED = "tip_changed"
EVENT_SESSION_STATUS = "session_status"
EVENT_ITEMS_UPDATED = "items_updated"


class ConnectionManager:
    """Manages WebSocket connections grouped by session_id."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection for a session."""
        await websocket.accept()
        self._connections.setdefault(session_id, set()).add(websocket)
        logger.info(
            "WS connected: session=%s, total=%d",
            session_id,
            len(self._connections[session_id]),
        )

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if session_id in self._connections:
            self._connections[session_id].discard(websocket)
            if not self._connections[session_id]:
                del self._connections[session_id]

    async def broadcast(self, session_id: str, event: dict) -> None:
        """Send an event to all connected clients in a session."""
        connections = self._connections.get(session_id, set()).copy()
        for ws in connections:
            try:
                await ws.send_json(event)
            except Exception:
                logger.warning("WS send failed, disconnecting")
                self.disconnect(session_id, ws)

    def get_connection_count(self, session_id: str) -> int:
        """Return the number of active connections for a session."""
        return len(self._connections.get(session_id, set()))
