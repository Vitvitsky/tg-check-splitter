# Task: Implement session CRUD routes

## Parent Domain
003-api-routes

## Description
Реализовать все endpoints для управления сессиями в `api/routes/sessions.py`.

### Endpoints:

1. **POST /api/sessions** — создать сессию
   - Auth: required
   - Body: `SessionCreateIn`
   - Вызывает: `SessionService.create_session(user.id, user.first_name)`
   - Returns: `SessionOut` (201)

2. **GET /api/sessions/{invite_code}** — получить сессию по invite_code
   - Auth: required
   - Вызывает: `SessionService.get_session_by_invite(invite_code)`
   - Returns: `SessionOut` или 404

3. **GET /api/sessions/id/{session_id}** — получить сессию по ID
   - Auth: required
   - Проверка: пользователь — member сессии
   - Returns: `SessionOut` или 404/403

4. **POST /api/sessions/{invite_code}/join** — присоединиться
   - Auth: required
   - Вызывает: `SessionService.join_session(invite_code, user.id, user.first_name)`
   - Returns: `MemberOut` (201) или 409 (already joined) или 404

5. **POST /api/sessions/{session_id}/finish** — завершить голосование (admin only)
   - Auth: required, admin check
   - Вызывает: `SessionService.update_status(session_id, "closed")`
   - Returns: 200

6. **POST /api/sessions/{session_id}/settle** — расчёт (admin only)
   - Auth: required, admin check
   - Вызывает: `calculate_shares()` с данными сессии
   - Вызывает: `SessionService.update_status(session_id, "settled")`
   - Returns: `list[ShareOut]`

7. **GET /api/sessions/my** — мои сессии (для HomePage)
   - Auth: required
   - Вызывает: SQL query для сессий где user — member
   - Returns: `list[SessionBrief]`

### Хелпер для проверки admin:
```python
def require_admin(session: Session, user: TelegramUser):
    if session.admin_tg_id != user.id:
        raise HTTPException(403, "Admin only")
```

### Хелпер для проверки membership:
```python
def require_member(session: Session, user: TelegramUser):
    member_ids = {m.user_tg_id for m in session.members}
    if user.id not in member_ids:
        raise HTTPException(403, "Not a member")
```

## Files to Create/Modify
- api/routes/sessions.py (create)
- api/app.py (modify) — include sessions router

## Dependencies
- 001-02-auth-middleware
- 001-03-db-dependency
- 001-04-app-factory
- 002-01-response-schemas
- 002-02-request-schemas

## Tests Required
- `tests/test_api/test_sessions.py`:
  - test_create_session
  - test_get_session_by_invite
  - test_get_session_by_invite_not_found
  - test_join_session
  - test_join_session_already_joined
  - test_finish_session_admin
  - test_finish_session_not_admin → 403
  - test_settle_session
  - test_my_sessions

## Acceptance Criteria
- [ ] Все 7 endpoints реализованы
- [ ] Auth проверка на каждом endpoint
- [ ] Admin check на finish/settle
- [ ] Member check на get by ID
- [ ] Корректные HTTP коды (201, 200, 403, 404, 409)
- [ ] Тесты проходят

## Estimated Complexity
L

## Status: done
## Assigned: worker-7928
