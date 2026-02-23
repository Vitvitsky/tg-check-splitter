# Domain: API Foundation

## Priority
HIGH

## Scope
- FastAPI app factory (`api/app.py`) с CORS, lifespan (DB engine init)
- Telegram initData HMAC-SHA256 auth (`api/auth.py`) — валидация подписи, проверка auth_date (<24ч), FastAPI Dependency `get_current_user() -> TelegramUser`
- DB session dependency (`api/deps.py`) — переиспользует `bot/db.py` `get_async_session()`
- Entrypoint (`api/__main__.py`) — uvicorn запуск
- Обновление `pyproject.toml` — добавление fastapi, uvicorn, python-multipart
- Обновление `docker-compose.yml` — добавление api-сервиса

## Dependencies
- None (первый домен)

## Key Decisions
- Auth header: `Authorization: tma <initData>` (стандарт Telegram Mini Apps)
- HMAC: `HMAC_SHA256(HMAC_SHA256(bot_token, "WebAppData"), data_check_string)`
- TelegramUser dataclass: `id: int, first_name: str, last_name: str | None, username: str | None, language_code: str | None`
- DB dependency: `async def get_db() -> AsyncGenerator[AsyncSession, None]` через `get_async_session()`
- Settings: переиспользуем `bot/config.py` `get_settings()`, добавляем `webapp_url: str` для CORS
- Lifespan: при startup вызываем `get_engine()` для инициализации пула

## Acceptance Criteria
- FastAPI app создаётся через factory `create_app()`
- CORS разрешает только `settings.webapp_url`
- Auth dependency корректно валидирует initData и возвращает TelegramUser
- Auth отклоняет невалидную подпись (401) и expired initData (401)
- DB dependency предоставляет AsyncSession и закрывает после запроса
- `python -m api` запускает uvicorn сервер
- Тесты: auth validation (valid/invalid/expired), app creation
- Новые зависимости добавлены в pyproject.toml

## Estimated Tasks
- create api package structure
- implement auth.py (HMAC validation + dependency)
- implement deps.py (DB session dependency)
- implement app.py (factory + CORS + lifespan)
- implement __main__.py (entrypoint)
- update pyproject.toml
- update docker-compose.yml
- tests for auth
- tests for app/deps
