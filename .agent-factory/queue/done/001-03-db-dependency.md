# Task: Implement DB session dependency

## Parent Domain
001-api-foundation

## Description
Создать FastAPI dependency для получения AsyncSession, переиспользуя существующий `bot/db.py`.

```python
# api/deps.py
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from bot.db import get_async_session

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async_session = get_async_session()
    async with async_session() as session:
        yield session
```

## Files to Create/Modify
- api/deps.py (create)

## Dependencies
- 001-01-api-package-structure

## Tests Required
- `tests/test_api/test_deps.py`:
  - test_get_db_yields_session — проверить что dependency yield-ит AsyncSession
  - test_session_closed_after_use — проверить что сессия закрывается

## Acceptance Criteria
- [ ] get_db() возвращает AsyncSession
- [ ] Сессия корректно закрывается после yield
- [ ] Работает с существующим bot/db.py без модификаций
- [ ] Тесты проходят

## Estimated Complexity
S

## Status: done
## Assigned: worker-92947
