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
- [x] **UI Refactor** — переработка фронтенда по дизайну из `design/mini-app.pen` (12 UI components, 4 bottom sheets, 5 new pages, 7 refactored pages)
- [ ] Ready for deployment

## Phase: UI Refactor (Current)

Рефакторинг webapp по 18 экранам из дизайна в Pencil (`design/mini-app.pen`).
Дизайн-система: 31 компонент (Button, Input, Card, List, Badge, Chip, Avatar, Nav, BottomSheet, Snackbar).

### Задачи

#### 1. Shared UI Components (design system)
Создать переиспользуемые компоненты по дизайн-системе из .pen:
- `BottomSheet` — модальный лист снизу (используется в EditItem, AddItem, CustomTip, AddGuest)
- `Header` — навигационный хедер с back/action кнопками
- `BottomBar` — нижняя навигация (Home/People/Settings)
- `Button` — Primary, Secondary, Destructive, Ghost, Icon, MainAction
- `Badge` — Default, Success, Warning
- `Chip/ChipActive` — для tip selection
- `Avatar/AvatarSmall` — аватары участников
- `Card` — секционная карточка
- `ListItem/Separator` — элемент списка с разделителем
- `ReceiptItem` — элемент чека (имя, qty, цена)
- `MemberCard` — карточка участника (аватар, имя, сумма, бейджи)
- `Snackbar` — уведомления

#### 2. Refactor Existing Pages
По дизайну переработать:
- `HomePage` → Screen/Home (session cards, bottom nav, FAB)
- `ScanPage` → Screen/ScanReceipt + Screen/OCRProcessing (camera area, session name input)
- `EditItemsPage` → Screen/ReceiptReview + Screen/OCRWarning (receipt items list, warning banner, info bar)
- `VotingPage` → Screen/Voting (participant avatars, claim/quantity controls)
- `TipPage` → Screen/TipSummary (your items, tip chips, summary card)
- `SettlePage` → Screen/Settlement (status banner, member list, total card)
- `JoinPage` → Screen/JoinSession (success area, session info card)

#### 3. New Pages
- `VotingAdminPage` → Screen/VotingAdmin (progress card, member list with badges, reminder action)
- `UnvotedItemsPage` → Screen/UnvotedItems (split equally / remove per item, reopen voting)
- `PaymentQuotaPage` → Screen/PaymentQuota (limit info, plan cards, Stars purchase)
- `SessionHistoryPage` → Screen/SessionHistory (settled session detail, participants, your items)
- `ShareSessionPage` → Screen/ShareSession (QR code, invite link, share buttons)

#### 4. New Bottom Sheets
- `EditItemSheet` → Screen/EditItem (name, price, qty fields, delete/save)
- `AddItemSheet` → Screen/AddItem (name, price, qty fields, add button)
- `CustomTipSheet` → Screen/CustomTip (percentage input, calculated amount, apply)
- `AddGuestSheet` → Screen/AddGuest (name input, dish checkboxes, add button)

#### 5. Routing & Navigation
- Добавить маршруты для новых страниц
- Bottom navigation (Home/People/Settings)
- Унифицировать Header с back button
