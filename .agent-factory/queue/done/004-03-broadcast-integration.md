# Task: Integrate WebSocket broadcast into REST routes

## Parent Domain
004-websocket

## Description
Добавить broadcast вызовы в мутирующие REST endpoints, чтобы WebSocket клиенты получали real-time уведомления.

### Точки интеграции:

1. **POST /api/sessions/{id}/vote** (voting.py)
   - После `cycle_vote()` → broadcast `{"type": "vote_updated", "data": {"item_id": ..., "user_tg_id": ..., "quantity": ...}}`

2. **POST /api/sessions/{invite_code}/join** (sessions.py)
   - После `join_session()` → broadcast `{"type": "member_joined", "data": {"user_tg_id": ..., "display_name": ...}}`

3. **POST /api/sessions/{id}/confirm** (voting.py)
   - После `confirm_member()` → broadcast `{"type": "member_confirmed", "data": {"user_tg_id": ...}}`

4. **POST /api/sessions/{id}/unconfirm** (voting.py)
   - После `unconfirm_member()` → broadcast `{"type": "member_unconfirmed", "data": {"user_tg_id": ...}}`

5. **POST /api/sessions/{id}/tip** (voting.py)
   - После `set_member_tip()` → broadcast `{"type": "tip_changed", "data": {"user_tg_id": ..., "tip_percent": ...}}`

6. **POST /api/sessions/{id}/finish** (sessions.py)
   - После `update_status()` → broadcast `{"type": "session_status", "data": {"status": "closed"}}`

7. **PUT /api/sessions/{id}/items** (ocr.py)
   - После обновления позиций → broadcast `{"type": "items_updated", "data": {"items": [...]}}`

### Получение manager в routes:
```python
from fastapi import Request

# В каждом route добавить параметр:
async def vote(request: Request, ...):
    manager: ConnectionManager = request.app.state.ws_manager
    # ... do mutation ...
    await manager.broadcast(str(session_id), {"type": "vote_updated", "data": {...}})
```

### Важно:
- Broadcast не должен блокировать response — если WS ошибка, response всё равно 200
- Broadcast идёт ПОСЛЕ успешной записи в БД

## Files to Create/Modify
- api/routes/sessions.py (modify) — добавить broadcast в join, finish
- api/routes/voting.py (modify) — добавить broadcast в vote, tip, confirm, unconfirm
- api/routes/ocr.py (modify) — добавить broadcast в items update

## Dependencies
- 004-01-connection-manager
- 004-02-ws-endpoint
- 003-01-session-routes
- 003-02-voting-routes
- 003-03-ocr-routes

## Tests Required
- `tests/test_api/test_ws_integration.py`:
  - test_vote_triggers_broadcast (mock ws_manager)
  - test_join_triggers_broadcast
  - test_confirm_triggers_broadcast

## Acceptance Criteria
- [ ] Все мутирующие endpoints вызывают broadcast
- [ ] Broadcast не блокирует HTTP response
- [ ] Event format соответствует спецификации
- [ ] Тесты проходят

## Estimated Complexity
M

## Status: done
## Assigned: worker-24518
