# Domain: WebSocket Real-Time

## Priority
MEDIUM

## Scope
- `api/ws.py` — ConnectionManager (группировка по session_id, connect/disconnect/broadcast)
- `api/routes/ws.py` — WebSocket endpoint `/ws/{session_id}`
- Интеграция с REST routes: broadcast после мутаций (vote, join, confirm, tip, items_updated, session_status)
- Auth через query param: `/ws/{session_id}?token=<initData>`

## Dependencies
- 001-api-foundation (auth для WS)
- 003-api-routes (нужно интегрировать broadcast в мутирующие endpoints)

## Key Decisions
- ConnectionManager — in-memory dict `{session_id: set[WebSocket]}`
- Heartbeat через ping/pong (WebSocket protocol level)
- Event types: `vote_updated`, `member_joined`, `member_confirmed`, `tip_changed`, `session_status`, `items_updated`
- Event format: `{"type": str, "data": dict}`
- При отключении — graceful remove из connections
- Manager — singleton, доступен через `app.state.ws_manager`

## Acceptance Criteria
- ConnectionManager корректно добавляет/удаляет соединения
- Broadcast отправляет event всем подключённым к session
- Auth валидация на WS подключении
- REST endpoints (vote, confirm, tip, join) вызывают broadcast
- Disconnected клиенты не вызывают ошибок при broadcast
- Тесты: ConnectionManager unit tests, WS endpoint integration tests

## Estimated Tasks
- ConnectionManager implementation
- WS endpoint with auth
- Event types definition
- Integrate broadcast into REST routes
- Tests
