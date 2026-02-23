# Project Goal

## Vision
Telegram Mini App для сплиттера чеков: миграция из inline-keyboards + FSM бота в полноценный SPA с веб-интерфейсом. Переиспользуем 100% существующей бизнес-логики (services, models, calculator, OCR). Пишем новый API-слой (FastAPI) + Frontend (React + TypeScript).

Детальный план миграции: `docs/plans/2026-02-21-mini-app-migration.md`

## Tech Stack
- Language: Python 3.12, TypeScript 5
- Backend: FastAPI + uvicorn (API-слой поверх существующих сервисов)
- Frontend: React 19 + Vite + Tailwind CSS 4 + @telegram-apps/sdk-react + TanStack Query
- Database: PostgreSQL + SQLAlchemy 2.x async (существующая БД, те же миграции)
- Real-time: WebSocket (FastAPI встроенный)
- Auth: Telegram initData HMAC-SHA256 validation
- Tests: pytest (backend), vitest (frontend)
- Linter: ruff (Python), ESLint (TypeScript)
- Package manager: uv (Python), npm (JS)

## Architecture Constraints
- Все эндпоинты FastAPI должны быть асинхронными
- Каждая модель должна иметь Pydantic-схему (request + response)
- 100% покрытие тестами для API endpoints
- Существующие сервисы (SessionService, OcrService, CalculatorService, QuotaService) используются as-is — без модификаций
- DB session через FastAPI dependency, переиспользуя `bot/db.py` get_async_session()
- Auth через `Authorization: tma <initData>` header (REST), query param (WebSocket)
- CORS только для домена Mini App
- Frontend: Telegram theme variables → Tailwind CSS custom properties
- Frontend: TanStack Query для серверного стейта, WS events → cache invalidation
- UUID primary keys, BigInteger для Telegram user IDs (как в существующих моделях)

## Domains
1. **001-api-foundation** (HIGH) — FastAPI app, auth (HMAC), DB dep, CORS, entrypoint
2. **002-api-schemas** (HIGH) — Pydantic request/response models для всех endpoints
3. **003-api-routes** (HIGH) — REST endpoints: sessions, voting, ocr, quota + тесты
4. **004-websocket** (MEDIUM) — ConnectionManager, WS endpoint, broadcast integration
5. **005-frontend-skeleton** (MEDIUM) — React/Vite/TS, TG SDK, routing, API client, WS hook
6. **006-frontend-pages** (LOW) — 7 страниц + shared components
7. **007-bot-integration** (LOW) — Bot ↔ Mini App bridge, notifications, Stars redirect

## Current Priority
HIGH: Backend API + Auth (Этап 1)
HIGH: Pydantic schemas
MEDIUM: WebSocket real-time (Этап 2)
MEDIUM: Frontend skeleton + routing (Этап 3)
LOW: Frontend screens (Этап 4)
LOW: Bot integration + polish (Этапы 5-6)

## Status
- [x] Planning complete (migration plan exists)
- [x] Core domain implemented (API + Auth) — 74 tests passing
- [x] WebSocket layer implemented (ConnectionManager + endpoint + broadcast integration)
- [x] Frontend skeleton (Vite + React + TG SDK + routing + API client + WS hook)
- [x] Frontend screens (7 pages + 9 shared components — build passing)
- [x] Bot integration (WebAppInfo buttons + push notifications via httpx)
- [x] Tests passing (74/74 API tests)
- [ ] Ready for deployment
