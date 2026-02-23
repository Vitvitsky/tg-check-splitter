# Task: Implement quota route

## Parent Domain
003-api-routes

## Description
Реализовать endpoint для получения информации о квоте пользователя в `api/routes/quota.py`.

### Endpoints:

1. **GET /api/quota** — информация о квоте текущего пользователя
   - Auth: required
   - Вызывает: `QuotaService(db, settings.free_scans_per_month).get_quota_info(user.id)`
   - Returns: `QuotaOut`

```python
router = APIRouter(prefix="/api/quota", tags=["quota"])

@router.get("", response_model=QuotaOut)
async def get_quota(
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    svc = QuotaService(db, settings.free_scans_per_month)
    free_left, paid, reset_at = await svc.get_quota_info(user.id)
    return QuotaOut(free_scans_left=free_left, paid_scans=paid, reset_at=reset_at)
```

## Files to Create/Modify
- api/routes/quota.py (create)
- api/app.py (modify) — include quota router

## Dependencies
- 001-02-auth-middleware
- 001-03-db-dependency
- 001-04-app-factory
- 002-01-response-schemas

## Tests Required
- `tests/test_api/test_quota.py`:
  - test_get_quota — returns QuotaOut with correct fields
  - test_get_quota_unauthenticated → 401/422

## Acceptance Criteria
- [ ] GET /api/quota возвращает QuotaOut
- [ ] Auth проверка
- [ ] Тесты проходят

## Estimated Complexity
S

## Status: done
## Assigned: worker-7979
