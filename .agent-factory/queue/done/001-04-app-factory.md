# Task: Implement FastAPI app factory with CORS and lifespan

## Parent Domain
001-api-foundation

## Description
Реализовать `create_app()` factory в `api/app.py`:

1. **Lifespan**: при startup вызвать `get_engine()` для инициализации connection pool
2. **CORS**: разрешить origin из `settings.webapp_url` (плюс `http://localhost:5173` для dev)
3. **Router**: включить все route-модули с prefix `/api`
4. **Обновить Settings**: добавить поле `webapp_url: str = "http://localhost:5173"` в `bot/config.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from bot.config import get_settings
from bot.db import get_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_engine()  # Initialize connection pool
    yield

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Check Splitter API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.webapp_url, "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Include routers (будут добавлены в задачах 003-*)
    return app
```

## Files to Create/Modify
- api/app.py (modify) — полная реализация create_app()
- bot/config.py (modify) — добавить webapp_url в Settings

## Dependencies
- 001-01-api-package-structure
- 001-02-auth-middleware
- 001-03-db-dependency

## Tests Required
- `tests/test_api/test_app.py`:
  - test_create_app — app создаётся, тип FastAPI
  - test_cors_headers — CORS заголовки присутствуют в response
  - test_health_endpoint — GET /api/health → 200 (добавить простой health check)

## Acceptance Criteria
- [ ] create_app() возвращает настроенное FastAPI приложение
- [ ] CORS middleware настроен с webapp_url
- [ ] Lifespan инициализирует DB engine
- [ ] webapp_url добавлен в Settings с default значением
- [ ] Health check endpoint работает
- [ ] Тесты проходят

## Estimated Complexity
S

## Status: done
## Assigned: worker-3332
