# Task: Implement WebSocket endpoint with auth

## Parent Domain
004-websocket

## Description
Реализовать WebSocket endpoint `/ws/{session_id}` с аутентификацией через query parameter.

### Endpoint:
```
WS /ws/{session_id}?token=<initData>
```

WebSocket не поддерживает custom headers, поэтому initData передаётся через query param `token`.

### Логика:
1. Валидировать `token` через ту же функцию `validate_init_data()`
2. Проверить что user — member сессии
3. Подключить к ConnectionManager
4. Слушать входящие сообщения (ping/keep-alive) в бесконечном цикле
5. При disconnect — убрать из ConnectionManager

### Хранение manager:
ConnectionManager — singleton в `app.state.ws_manager`.
Создаётся в lifespan `create_app()`:
```python
app.state.ws_manager = ConnectionManager()
```

### Доступ из routes:
```python
def get_ws_manager(request: Request) -> ConnectionManager:
    return request.app.state.ws_manager
```

## Files to Create/Modify
- api/routes/ws.py (create) — WebSocket endpoint
- api/app.py (modify) — добавить ws_manager в state + include WS router

## Dependencies
- 004-01-connection-manager
- 001-02-auth-middleware (validate_init_data)
- 001-04-app-factory (app.state)

## Tests Required
- `tests/test_api/test_ws.py` (дополнить):
  - test_ws_connect_authenticated
  - test_ws_connect_no_token → close
  - test_ws_connect_invalid_token → close
  - test_ws_receives_broadcast

## Acceptance Criteria
- [ ] WS endpoint доступен по /ws/{session_id}
- [ ] Auth через query param token
- [ ] Невалидный token → connection close
- [ ] ConnectionManager обновляется при connect/disconnect
- [ ] Тесты проходят

## Estimated Complexity
M

## Status: done
## Assigned: worker-18980
