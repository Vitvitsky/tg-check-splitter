# Telegram Mini App Migration Plan

> Миграция check-splitter бота из чисто-ботового интерфейса (inline keyboards + FSM) в Telegram Mini App с веб-интерфейсом.

## Мотивация

### Проблемы текущего UI на inline-кнопках
- Пагинация (8 позиций на страницу) — неудобно при 20+ позициях
- Нет визуального прогресса: кто что выбрал, в реальном времени
- Редактирование позиций через FSM-диалог (имя - цена) — многошаговое и ломкое
- Inline-кнопки не поддерживают drag & drop, свайпы, анимации
- Нельзя одновременно видеть свой выбор и итог

### Что даёт Mini App
- Полноценный SPA: все позиции видны сразу, скролл вместо пагинации
- Real-time обновления через WebSocket (кто что отмечает — видно мгновенно)
- Нативное редактирование: inline-edit, свайп для удаления
- Визуальная сводка: кто подтвердил, кто нет, прогресс-бар
- Фото чека можно показать рядом с позициями
- Удобный выбор чаевых через slider вместо preset-кнопок
- Лучшая навигация между экранами (tabs, swipe)

---

## Архитектура

```
┌────────────────────────────────┐
│     Telegram Mini App (SPA)    │  ← React + Vite + @telegram-apps/sdk-react
│                                │
│  Экраны:                       │
│  1. Главная (сессии)           │
│  2. Фото + OCR                 │
│  3. Редактирование позиций     │
│  4. Голосование                │
│  5. Чаевые + итог              │
│  6. Финальный расчёт           │
└────────────┬───────────────────┘
             │ HTTPS + WebSocket
┌────────────▼───────────────────┐
│     FastAPI Backend (новый)     │  ← API-слой поверх существующих сервисов
│                                 │
│  REST:                          │
│  POST /api/sessions             │  ← создать сессию
│  GET  /api/sessions/{code}      │  ← данные сессии по invite_code
│  POST /api/sessions/{id}/join   │  ← присоединиться
│  POST /api/sessions/{id}/photos │  ← загрузить фото чека
│  POST /api/sessions/{id}/ocr    │  ← запустить OCR
│  PUT  /api/sessions/{id}/items  │  ← редактировать позиции
│  POST /api/sessions/{id}/vote   │  ← проголосовать
│  POST /api/sessions/{id}/tip    │  ← выбрать чаевые
│  POST /api/sessions/{id}/confirm│  ← подтвердить выбор
│  POST /api/sessions/{id}/finish │  ← завершить голосование
│  POST /api/sessions/{id}/settle │  ← расчёт
│  GET  /api/sessions/{id}/shares │  ← текущие доли
│  GET  /api/quota                │  ← квота пользователя
│                                 │
│  WebSocket:                     │
│  /ws/{session_id}               │  ← real-time: votes, joins, confirms
│                                 │
│  Auth:                          │
│  initData HMAC validation       │  ← Telegram WebApp auth
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│  Существующие сервисы (as-is)  │  ← переиспользуем без изменений
│                                │
│  SessionService                │
│  OcrService                    │
│  CalculatorService             │
│  QuotaService                  │
│  Models / DB / Alembic         │
└────────────────────────────────┘
             +
┌────────────────────────────────┐
│  aiogram bot (урезанный)       │  ← остаётся для:
│                                │
│  1. /start → открывает         │     Mini App через WebAppInfo
│  2. Deep link → redirect в     │     Mini App с invite_code
│  3. Push-уведомления           │     (итоги, новые участники)
│  4. Telegram Stars оплата      │     (пока нет Stars API в Mini App)
└────────────────────────────────┘
```

---

## Что переиспользуем без изменений

| Компонент | Файл | Почему работает as-is |
|-----------|------|----------------------|
| SessionService | `bot/services/session.py` | Чистый async, принимает `AsyncSession`, не зависит от aiogram |
| OcrService | `bot/services/ocr.py` | Принимает `list[bytes]`, возвращает `OcrResult` — transport-agnostic |
| CalculatorService | `bot/services/calculator.py` | Чистые функции: `calculate_shares()`, `calculate_user_share()` |
| QuotaService | `bot/services/quota.py` | Async, зависит только от SQLAlchemy |
| Models | `bot/models/` | SQLAlchemy ORM — работает с любым web framework |
| DB setup | `bot/db.py` | Lazy engine/session — подключается к той же Postgres |
| Alembic | `alembic/` | Миграции не зависят от runtime |
| Тесты | `tests/` | Тестируют сервисы, не хэндлеры |

---

## Tech Stack для Mini App

### Frontend
- **React 19** + **TypeScript**
- **Vite** — сборка и dev-server
- **@telegram-apps/sdk-react** — Telegram WebApp SDK (initData, theme, haptics, back button)
- **TanStack Query** — серверный стейт, кэширование, real-time updates
- **Tailwind CSS 4** — стилизация (Telegram theme variables через CSS custom properties)
- Нет тяжёлых UI-библиотек — кастомные компоненты под Telegram design language

### Backend
- **FastAPI** — API-фреймворк (тот же async Python, естественная интеграция с существующими сервисами)
- **uvicorn** — ASGI-сервер
- **python-multipart** — загрузка фото
- **websockets** (встроено в FastAPI) — real-time
- Авторизация через **HMAC-SHA256 валидацию initData**

### Инфраструктура
- **Frontend**: статика на Vercel / Cloudflare Pages (бесплатно, CDN, HTTPS)
- **Backend**: тот же сервер что и бот (или отдельный контейнер в docker-compose)
- **Postgres**: та же БД, те же миграции

---

## Стратегия миграции: поэтапная

Бот и Mini App работают параллельно. Каждый этап — самодостаточный инкремент.

---

### Этап 1: Backend API + Auth (фундамент)

**Цель:** FastAPI сервер с REST API, авторизация через Telegram initData.

**Новые файлы:**
```
api/
├── __init__.py
├── __main__.py          # uvicorn entrypoint
├── app.py               # FastAPI app factory
├── auth.py              # initData HMAC validation + dependency
├── deps.py              # DB session dependency (AsyncSession)
├── routes/
│   ├── __init__.py
│   ├── sessions.py      # CRUD сессий
│   ├── voting.py        # голосование
│   ├── ocr.py           # загрузка фото + OCR
│   └── quota.py         # квота
└── schemas.py           # Pydantic response/request models
```

**Задачи:**

1. **FastAPI app + config** (`api/app.py`)
   - CORS для Mini App домена
   - Lifespan: init DB engine
   - Mount static (если нужно)

2. **Auth middleware** (`api/auth.py`)
   - Парсинг `initData` из заголовка `Authorization: tma <initData>`
   - HMAC-SHA256 валидация: `HMAC_SHA256(HMAC_SHA256(bot_token, "WebAppData"), data_check_string)`
   - Проверка `auth_date` (не старше 24ч)
   - FastAPI Dependency: `get_current_user() -> TelegramUser`

3. **DB dependency** (`api/deps.py`)
   - Переиспользует `get_async_session()` из `bot/db.py`
   - `async def get_db() -> AsyncGenerator[AsyncSession]`

4. **Pydantic schemas** (`api/schemas.py`)
   - Request/Response модели для всех эндпоинтов
   - `SessionOut`, `ItemOut`, `VoteIn`, `ShareOut`, `OcrResultOut` и т.д.

5. **Session routes** (`api/routes/sessions.py`)
   - `POST /api/sessions` → `SessionService.create_session()`
   - `GET /api/sessions/{invite_code}` → `SessionService.get_session_by_invite()`
   - `POST /api/sessions/{id}/join` → `SessionService.join_session()`
   - `GET /api/sessions/{id}` → полные данные сессии с items, members, votes
   - `POST /api/sessions/{id}/finish` → `SessionService.update_status("closed")`
   - `POST /api/sessions/{id}/settle` → `calculate_shares()` + update status

6. **Voting routes** (`api/routes/voting.py`)
   - `POST /api/sessions/{id}/vote` → `SessionService.cycle_vote()`
   - `POST /api/sessions/{id}/tip` → `SessionService.set_member_tip()`
   - `POST /api/sessions/{id}/confirm` → `SessionService.confirm_member()`
   - `GET /api/sessions/{id}/shares` → `calculate_shares()` / `calculate_user_share()`

7. **OCR routes** (`api/routes/ocr.py`)
   - `POST /api/sessions/{id}/photos` → загрузка файлов, `SessionService.add_photo()`
   - `POST /api/sessions/{id}/ocr` → `OcrService.parse_receipt()`
   - `PUT /api/sessions/{id}/items` → CRUD позиций
   - `DELETE /api/sessions/{id}/items/{item_id}` → удалить позицию

8. **Quota routes** (`api/routes/quota.py`)
   - `GET /api/quota` → `QuotaService.get_quota_info()`

9. **Тесты API** (`tests/test_api/`)
   - Фикстура: `TestClient` с мок-initData
   - Тесты для auth, sessions, voting, OCR

**Зависимости (pyproject.toml):**
```toml
"fastapi>=0.115,<1",
"uvicorn[standard]>=0.34,<1",
"python-multipart>=0.0.20,<1",
```

**Результат:** Работающий API, который можно тестировать через curl/httpie.

---

### Этап 2: WebSocket для real-time

**Цель:** Участники видят изменения мгновенно (голоса, подтверждения, новые участники).

**Файлы:**
```
api/
├── ws.py                # WebSocket manager
└── routes/
    └── ws.py            # WebSocket endpoint
```

**Задачи:**

1. **ConnectionManager** (`api/ws.py`)
   - Группировка по `session_id`
   - `connect(session_id, websocket)`, `disconnect(...)`, `broadcast(session_id, event)`
   - Heartbeat (ping/pong)

2. **WebSocket endpoint** (`api/routes/ws.py`)
   - `WS /ws/{session_id}?token=<initData>`
   - Auth через query param (WebSocket не поддерживает заголовки)
   - Events (server → client):
     ```json
     {"type": "vote_updated", "item_id": "...", "user_id": 123, "quantity": 2}
     {"type": "member_joined", "user_id": 123, "name": "Alice"}
     {"type": "member_confirmed", "user_id": 123}
     {"type": "tip_changed", "user_id": 123, "tip_percent": 10}
     {"type": "session_status", "status": "closed"}
     {"type": "items_updated", "items": [...]}
     ```

3. **Интеграция с REST routes:**
   - Каждый мутирующий endpoint (vote, confirm, tip, join) после записи в БД вызывает `manager.broadcast()`
   - Broadcast идёт всем подключённым к этой сессии

**Результат:** Открыл Mini App → подключился к WS → видишь все изменения live.

---

### Этап 3: Frontend — скелет и навигация

**Цель:** SPA с роутингом, Telegram SDK интеграция, базовые экраны.

**Структура:**
```
webapp/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── src/
│   ├── main.tsx              # React entry + TelegramProvider
│   ├── App.tsx               # Router
│   ├── api/
│   │   ├── client.ts         # fetch wrapper с initData auth
│   │   ├── queries.ts        # TanStack Query hooks
│   │   └── ws.ts             # WebSocket client hook
│   ├── pages/
│   │   ├── HomePage.tsx      # Мои сессии + "Новый чек"
│   │   ├── ScanPage.tsx      # Фото + OCR
│   │   ├── EditItemsPage.tsx # Редактирование позиций
│   │   ├── VotingPage.tsx    # Выбор блюд
│   │   ├── TipPage.tsx       # Чаевые + сводка
│   │   ├── SettlePage.tsx    # Финальный расчёт
│   │   └── JoinPage.tsx      # Присоединение по invite_code
│   ├── components/
│   │   ├── ItemCard.tsx      # Карточка позиции (голосование)
│   │   ├── MemberAvatar.tsx  # Аватар участника
│   │   ├── TipSlider.tsx     # Слайдер чаевых
│   │   ├── ShareCard.tsx     # Карточка доли
│   │   ├── ProgressBar.tsx   # Прогресс подтверждений
│   │   └── QRCode.tsx        # QR-код для invite
│   ├── hooks/
│   │   ├── useSession.ts     # Загрузка/обновление сессии
│   │   ├── useWebSocket.ts   # WS подключение + events
│   │   └── useTelegram.ts    # Telegram SDK хелперы
│   └── lib/
│       ├── theme.ts          # Telegram theme → CSS variables
│       └── format.ts         # Форматирование цен/валют
```

**Задачи:**

1. **Инициализация проекта**
   - `npm create vite@latest webapp -- --template react-ts`
   - Tailwind CSS 4, TanStack Query, @telegram-apps/sdk-react
   - Vite proxy для dev (`/api` → `localhost:8000`)

2. **Telegram SDK integration** (`src/main.tsx`)
   - `<TelegramProvider>` — инициализация WebApp
   - Theme sync: маппинг Telegram CSS vars на Tailwind
   - Back button handler
   - Haptic feedback на действиях
   - `MainButton` для ключевых CTA

3. **API client** (`src/api/client.ts`)
   - `fetchWithAuth(url, options)` — добавляет `Authorization: tma <initData>`
   - Обработка ошибок (401, 403, 500)
   - Base URL из env

4. **TanStack Query hooks** (`src/api/queries.ts`)
   - `useSession(code)` — данные сессии
   - `useVoteMutation()` — голосование (optimistic update)
   - `useConfirmMutation()` — подтверждение
   - `useTipMutation()` — чаевые
   - `useShares(sessionId)` — текущие доли
   - `useQuota()` — квота

5. **WebSocket hook** (`src/api/ws.ts`, `src/hooks/useWebSocket.ts`)
   - Auto-reconnect с backoff
   - Invalidate TanStack Query при получении events
   - Typed events: `VoteUpdated | MemberJoined | MemberConfirmed | ...`

6. **Роутинг** (`src/App.tsx`)
   - `/` — HomePage (список сессий)
   - `/scan` — ScanPage
   - `/session/:code` — JoinPage → VotingPage
   - `/session/:code/edit` — EditItemsPage
   - `/session/:code/vote` — VotingPage
   - `/session/:code/tip` — TipPage
   - `/session/:code/settle` — SettlePage

**Результат:** Работающий каркас SPA с навигацией, авторизацией, real-time подключением.

---

### Этап 4: Frontend — экраны

**Цель:** Реализация всех экранов приложения.

#### 4.1 HomePage — Главная
- Кнопка "📸 Новый чек" → переход на ScanPage
- Список активных сессий пользователя (если есть)
- Квота (бесплатных осталось / оплаченных)

#### 4.2 ScanPage — Фото + OCR
- Кнопка загрузки фото (камера или галерея)
- Превью загруженных фото (можно удалить)
- Кнопка "Распознать" → показ спиннера → результат
- Результат OCR: список позиций с ценами
- Предупреждение при mismatch суммы
- CTA: "Всё верно" / "Редактировать"

#### 4.3 EditItemsPage — Редактирование позиций
- Список позиций — inline-edit (тап → меняешь текст/цену)
- Свайп влево → удалить
- Кнопка "+" → добавить позицию
- Итого внизу (пересчитывается в реальном времени)
- CTA: "Начать голосование" → генерирует QR + invite link

#### 4.4 JoinPage — Присоединение
- При открытии Mini App по deep link с invite_code
- Показывает: название сессии, админ, количество участников
- Кнопка "Присоединиться" → redirect на VotingPage

#### 4.5 VotingPage — Голосование (ключевой экран)
- Все позиции видны (scroll, не пагинация!)
- Каждая позиция — карточка:
  - Название, цена, количество
  - Кнопка +/- для quantity (cycle: 0→1→2→...→0)
  - Аватары/фишки тех, кто уже отметил
  - Real-time обновление через WebSocket
- Внизу: "Твой текущий итог: 1250₽"
- CTA: MainButton "Далее → Чаевые"
- Haptic feedback при голосовании

#### 4.6 TipPage — Чаевые + личная сводка
- Слайдер: 0%–25% (с preset-значениями 0, 5, 10, 15)
- Разбивка:
  - Список выбранных блюд с ценами
  - Подитог
  - Чаевые (X%)
  - **Итого: Y₽**
- CTA: MainButton "Подтвердить"

#### 4.7 SettlePage — Финальный расчёт (для админа)
- Прогресс: "Подтвердили: 3/5" с аватарами
- Таблица долей: имя → сумма
- Список неотмеченных позиций (если есть):
  - Опции: разделить поровну / убрать из счёта / вернуть голосование
- CTA: "Завершить и отправить итоги"

**Результат:** Полностью функциональный Mini App.

---

### Этап 5: Интеграция с ботом

**Цель:** Бот открывает Mini App, отправляет уведомления, обрабатывает платежи.

**Задачи:**

1. **Обновить `/start`**
   - Без deep link: показать кнопку `WebAppInfo(url="https://app.example.com/")`
   - С deep link (`/start {code}`): открыть Mini App с `?startapp={code}`

2. **Обновить QR/invite генерацию**
   - Ссылка: `https://t.me/botname/appname?startapp={invite_code}`
   - QR-код указывает на эту ссылку

3. **Push-уведомления через бота**
   - API endpoint `POST /api/notify` (internal, bot → API или напрямую)
   - При завершении сессии: бот отправляет каждому участнику сообщение с их долей
   - При новом участнике: уведомление админу

4. **Telegram Stars (остаётся в боте)**
   - Пока Telegram Stars API недоступно в Mini App
   - При нехватке квоты: Mini App показывает "Оплатите в боте" с кнопкой → переход в чат бота
   - Бот обрабатывает оплату, пишет в БД
   - Mini App при следующем запросе видит обновлённую квоту

5. **BotFather настройка**
   - `/setmenubutton` → URL Mini App
   - Или inline-кнопка `WebAppInfo` в ответе на `/start`

**Результат:** Бот и Mini App работают как единое целое.

---

### Этап 6: Оптимизация и полировка

1. **Offline/slow network**
   - Optimistic updates для голосования (UI обновляется мгновенно, синк с сервером async)
   - Skeleton loading states
   - Error boundaries + retry

2. **Производительность**
   - Lazy loading экранов (React.lazy + Suspense)
   - Мемоизация компонентов (React.memo для ItemCard)
   - Debounce для слайдера чаевых

3. **UX polish**
   - Haptic feedback: `impactOccurred('light')` при голосовании, `notificationOccurred('success')` при подтверждении
   - Smooth анимации (Framer Motion или CSS transitions)
   - Pull-to-refresh для обновления данных
   - Telegram theme: поддержка light/dark mode
   - Адаптация под размер устройства (compact/expanded Mini App)

4. **Безопасность**
   - Rate limiting на API эндпоинтах
   - Валидация прав: только админ может finish/settle/edit items
   - Sanitization: XSS-защита в названиях позиций (из OCR)
   - CORS: только домен Mini App

5. **Мониторинг**
   - Логирование API запросов
   - Sentry для frontend ошибок
   - Health check endpoint

---

## Изменения в pyproject.toml

```toml
[project]
dependencies = [
    # Existing
    "aiogram[i18n]>=3.15,<4",
    "sqlalchemy[asyncio]>=2.0,<3",
    "asyncpg>=0.30,<1",
    "alembic>=1.14,<2",
    "httpx>=0.28,<1",
    "pydantic>=2.0,<3",
    "pydantic-settings>=2.0,<3",
    "qrcode[pil]>=8.0,<9",
    # New for Mini App API
    "fastapi>=0.115,<1",
    "uvicorn[standard]>=0.34,<1",
    "python-multipart>=0.0.20,<1",
]
```

---

## Изменения в docker-compose.yml

```yaml
services:
  bot:
    build: .
    command: python -m bot
    env_file: .env
    depends_on:
      db:
        condition: service_healthy

  api:
    build: .
    command: uvicorn api.app:create_app --factory --host 0.0.0.0 --port 8000
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:17-alpine
    # ... existing config
```

---

## Изменения в .env

```env
# Existing
BOT_TOKEN=...
OPENROUTER_API_KEY=...
DATABASE_URL=...

# New
WEBAPP_URL=https://your-miniapp.vercel.app
WEBAPP_SECRET=<generated>  # для дополнительных internal API вызовов
```

---

## Оценка трудозатрат

| Этап | Описание | Оценка |
|------|----------|--------|
| 1 | Backend API + Auth | 2-3 дня |
| 2 | WebSocket real-time | 1 день |
| 3 | Frontend скелет | 2 дня |
| 4 | Frontend экраны | 4-5 дней |
| 5 | Интеграция с ботом | 1 день |
| 6 | Полировка | 2-3 дня |
| **Итого** | | **12-15 дней** |

---

## Миграция данных

Не нужна. Та же БД, те же таблицы, те же миграции. Новый API-слой читает и пишет в те же модели.

---

## Риски и решения

| Риск | Решение |
|------|---------|
| Telegram Stars не работает в Mini App | Оставляем оплату в боте, Mini App перенаправляет |
| WebSocket теряет соединение | Auto-reconnect + fallback на polling (refetch TanStack Query) |
| initData expiration (24h) | При 401 — показать "Переоткройте приложение" |
| Загрузка фото: размер файлов | Ресайз на клиенте перед upload (canvas → blob), лимит 5MB |
| SEO/sharing | Не актуально — Mini App открывается только из Telegram |
| Старые пользователи привыкли к боту | Параллельная работа: бот всё ещё принимает фото и команды |

---

## Статус реализации

| Этап | Статус | Заметки |
|------|--------|---------|
| 1. Backend API + Auth | ✅ Done | 74 API tests passing |
| 2. WebSocket real-time | ✅ Done | ConnectionManager + broadcast |
| 3. Frontend скелет | ✅ Done | Vite + React + TG SDK + routing |
| 4. Frontend экраны | ✅ Done | 7 original pages |
| 5. Интеграция с ботом | ✅ Done | WebAppInfo + push notifications |
| 6. UI Refactor (дизайн) | ✅ Done | 18 экранов из design/mini-app.pen |

### UI Refactor (Этап 6b) — март 2026

Полная переработка фронтенда по дизайн-макетам из `design/mini-app.pen` (Pencil).

**Дизайн-система (12 компонентов):**
`webapp/src/components/ui/` — BottomSheet, Header, Button (5 вариантов), Avatar, Badge (3 вариантов), Chip, Card, SectionLabel, Separator, ReceiptItem, MemberCard, CtaBar

**Bottom Sheets (4 диалога):**
`webapp/src/components/sheets/` — EditItemSheet, AddItemSheet, CustomTipSheet, AddGuestSheet

**Новые страницы (5):**
- VotingAdminPage — прогресс голосования, список участников, напоминания
- UnvotedItemsPage — невостребованные позиции (split equally / remove)
- PaymentQuotaPage — лимиты сканов, покупка за Stars
- SessionHistoryPage — детали завершённой сессии
- ShareSessionPage — QR код + invite link + share buttons

**Обновлённая структура фронтенда:**
```
webapp/src/
├── components/
│   ├── ui/           # 12 design system components
│   ├── sheets/       # 4 bottom sheet dialogs
│   ├── SessionCard.tsx
│   ├── ItemCard.tsx
│   ├── PhotoPreview.tsx
│   └── ...
├── pages/            # 12 pages (lazy loaded)
│   ├── HomePage.tsx
│   ├── ScanPage.tsx
│   ├── EditItemsPage.tsx
│   ├── VotingPage.tsx
│   ├── TipPage.tsx
│   ├── SettlePage.tsx
│   ├── JoinPage.tsx
│   ├── VotingAdminPage.tsx
│   ├── UnvotedItemsPage.tsx
│   ├── PaymentQuotaPage.tsx
│   ├── SessionHistoryPage.tsx
│   └── ShareSessionPage.tsx
├── api/              # client, types, queries
├── hooks/            # useTelegram, useWebSocket
└── lib/              # resize
```

**Маршруты (12):**
```
/                           HomePage
/scan                       ScanPage
/quota                      PaymentQuotaPage
/session/:code              JoinPage
/session/:code/edit         EditItemsPage
/session/:code/vote         VotingPage
/session/:code/tip          TipPage
/session/:code/settle       SettlePage
/session/:code/admin        VotingAdminPage
/session/:code/unvoted      UnvotedItemsPage
/session/:code/share        ShareSessionPage
/session/:code/history      SessionHistoryPage
```

---

## Итого

Переход на Mini App:
- **Переиспользуем 100% бизнес-логики** (services, models, calculator, OCR)
- **Пишем заново**: API-слой (~15% кода) + Frontend (~60% усилий)
- **Бот остаётся**: для /start, уведомлений, оплаты Stars
- **Стратегия**: поэтапная миграция, бот и Mini App работают параллельно
