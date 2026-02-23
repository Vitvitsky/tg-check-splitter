# Task: Implement voting routes

## Parent Domain
003-api-routes

## Description
Реализовать endpoints для голосования, чаевых и подтверждения в `api/routes/voting.py`.

### Endpoints:

1. **POST /api/sessions/{session_id}/vote** — проголосовать (cycle quantity)
   - Auth: required, member check
   - Body: `VoteIn` (item_id)
   - Вызывает: `SessionService.cycle_vote(item_id, user.id, item.quantity)`
   - Returns: `{"quantity": int, "overflow_prevented": bool}`

2. **POST /api/sessions/{session_id}/tip** — установить чаевые
   - Auth: required, member check
   - Body: `TipIn` (tip_percent)
   - Вызывает: `SessionService.set_member_tip(session_id, user.id, tip_percent)`
   - Returns: 200

3. **POST /api/sessions/{session_id}/confirm** — подтвердить выбор
   - Auth: required, member check
   - Вызывает: `SessionService.confirm_member(session_id, user.id)`
   - Returns: 200

4. **POST /api/sessions/{session_id}/unconfirm** — отменить подтверждение (re-vote)
   - Auth: required, member check
   - Вызывает: `SessionService.unconfirm_member(session_id, user.id)`
   - Returns: 200

5. **GET /api/sessions/{session_id}/shares** — текущие доли всех
   - Auth: required, member check
   - Собирает данные из session.items + votes + members
   - Вызывает: `calculate_shares(items, session.tip_percent, per_person_tips)`
   - Returns: `list[ShareOut]`

6. **GET /api/sessions/{session_id}/my-share** — моя доля
   - Auth: required, member check
   - Вызывает: `calculate_user_share(items, user.id, tip_percent)`
   - Returns: `ShareOut`

### Важно: формат items для calculate_shares
```python
items_data = [
    {
        "price": item.price,
        "quantity": item.quantity,
        "votes": {v.user_tg_id: v.quantity for v in item.votes}
    }
    for item in session.items
]
per_person_tips = {m.user_tg_id: m.tip_percent for m in session.members if m.tip_percent is not None}
```

## Files to Create/Modify
- api/routes/voting.py (create)
- api/app.py (modify) — include voting router

## Dependencies
- 001-02-auth-middleware
- 001-03-db-dependency
- 001-04-app-factory
- 002-01-response-schemas
- 002-02-request-schemas

## Tests Required
- `tests/test_api/test_voting.py`:
  - test_vote_cycle — 0→1→2→0
  - test_vote_not_member → 403
  - test_set_tip
  - test_set_tip_invalid → 422
  - test_confirm
  - test_unconfirm
  - test_get_shares
  - test_get_my_share

## Acceptance Criteria
- [ ] Все 6 endpoints реализованы
- [ ] Member check на каждом endpoint
- [ ] calculate_shares() корректно вызывается с правильным форматом данных
- [ ] Тесты проходят

## Estimated Complexity
L

## Status: done
## Assigned: worker-7945
