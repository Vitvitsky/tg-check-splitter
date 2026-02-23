# Task: Implement WebSocket ConnectionManager

## Parent Domain
004-websocket

## Description
Реализовать ConnectionManager для управления WebSocket соединениями, сгруппированными по session_id.

```python
# api/ws.py
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}  # session_id → set of websockets

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections.setdefault(session_id, set()).add(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self._connections:
            self._connections[session_id].discard(websocket)
            if not self._connections[session_id]:
                del self._connections[session_id]

    async def broadcast(self, session_id: str, event: dict):
        """Send event to all connected clients in a session."""
        connections = self._connections.get(session_id, set()).copy()
        for ws in connections:
            try:
                await ws.send_json(event)
            except Exception:
                self.disconnect(session_id, ws)

    def get_connection_count(self, session_id: str) -> int:
        return len(self._connections.get(session_id, set()))
```

Event format:
```json
{"type": "vote_updated", "data": {"item_id": "...", "user_tg_id": 123, "quantity": 2}}
{"type": "member_joined", "data": {"user_tg_id": 123, "display_name": "Alice"}}
{"type": "member_confirmed", "data": {"user_tg_id": 123}}
{"type": "tip_changed", "data": {"user_tg_id": 123, "tip_percent": 10}}
{"type": "session_status", "data": {"status": "closed"}}
{"type": "items_updated", "data": {"items": [...]}}
```

## Files to Create/Modify
- api/ws.py (create) — ConnectionManager + event type constants

## Dependencies
- None (standalone class)

## Tests Required
- `tests/test_api/test_ws.py`:
  - test_connect_adds_to_connections
  - test_disconnect_removes
  - test_disconnect_cleans_empty_session
  - test_broadcast_sends_to_all
  - test_broadcast_handles_disconnected_client
  - test_get_connection_count

## Acceptance Criteria
- [ ] ConnectionManager работает корректно
- [ ] Broadcast не ломается при disconnected clients
- [ ] Empty sessions чистятся
- [ ] Тесты проходят

## Estimated Complexity
M

## Status: done
## Assigned: worker-18963
