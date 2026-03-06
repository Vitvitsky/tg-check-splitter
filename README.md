# Check Splitter Bot

Telegram-бот + Mini App для разделения ресторанного счёта между участниками.

## Как это работает

1. **Сканирование** — отправьте фото чека, LLM распознает позиции и валюту
2. **Редактирование** — проверьте и при необходимости исправьте список блюд
3. **Приглашение** — покажите QR-код или отправьте ссылку участникам
4. **Голосование** — каждый участник отмечает свои блюда (с поддержкой количества: 1/2, 2/2)
5. **Чаевые** — каждый выбирает свой процент чаевых и видит личную сводку
6. **Расчёт** — бот показывает итоги с индивидуальными суммами

## Быстрый старт

### Требования

- Python 3.12+
- Node.js 22+ (для сборки Mini App)
- PostgreSQL (через Docker)
- [uv](https://docs.astral.sh/uv/) — менеджер пакетов Python

### Локальная разработка

```bash
# Клонировать и установить зависимости
git clone <repo-url>
cd tg-check-splitter
uv sync --extra dev

# Скопировать и заполнить .env
cp .env.example .env
# Отредактировать .env: BOT_TOKEN, OPENROUTER_API_KEY, DATABASE_URL

# Запустить PostgreSQL
docker compose up -d db

# Применить миграции
uv run alembic upgrade head

# Запустить бота (long polling)
uv run python -m bot

# Запустить API-сервер (в отдельном терминале)
uv run python -m api
```

### Сборка Mini App (фронтенд)

```bash
cd webapp
npm install
npm run build   # -> webapp/dist/
```

API-сервер раздаёт собранный фронтенд из `webapp/dist/` как SPA.

### Docker (production)

```bash
docker compose up -d
```

Multi-stage сборка: Node.js собирает фронтенд, Python-образ запускает бота и API в одном контейнере. Entrypoint автоматически применяет миграции.

| Сервис | Порт | Описание |
|--------|------|----------|
| `app`  | 8005 | Бот + API + Mini App |
| `db`   | 5433 | PostgreSQL 17 |

---

## Переменные окружения

| Переменная | Тип | По умолчанию | Описание |
|---|---|---|---|
| `BOT_TOKEN` | str | — | Токен от [@BotFather](https://t.me/BotFather) |
| `OPENROUTER_API_KEY` | str | — | API-ключ [OpenRouter](https://openrouter.ai) |
| `OPENROUTER_MODEL` | str | `anthropic/claude-sonnet-4-5-20250929` | Vision-модель для OCR |
| `DATABASE_URL` | str | — | PostgreSQL URL (`postgresql+asyncpg://user:password@localhost:5433/checksplitter`) |
| `WEBAPP_URL` | str | `http://localhost:5173` | Базовый URL Mini App |
| `FREE_SCANS_PER_MONTH` | int | `3` | Лимит бесплатных сканирований в месяц |
| `SCAN_PRICE_STARS` | int | `1` | Цена платного сканирования в Telegram Stars |

---

## Архитектура

```
tg-check-splitter/
├── bot/                    # Telegram-бот (aiogram 3.x)
│   ├── handlers/           # Роутеры: start, check, voting, admin, payment
│   ├── services/           # Бизнес-логика: ocr, session, calculator, quota
│   ├── models/             # SQLAlchemy ORM-модели
│   ├── keyboards/          # Inline-клавиатуры
│   ├── config.py           # Pydantic Settings (lazy init)
│   ├── db.py               # Async engine + session factory
│   ├── middlewares.py      # DB session injection
│   └── i18n.py             # Gettext/Babel (ru/en)
├── api/                    # REST API + WebSocket (FastAPI)
│   ├── routes/             # Эндпоинты: sessions, voting, ocr, quota, ws
│   ├── services/           # Push-уведомления через Bot API
│   ├── auth.py             # Telegram Mini App HMAC-SHA256 валидация
│   ├── schemas.py          # Pydantic-схемы запросов/ответов
│   ├── ws.py               # WebSocket ConnectionManager
│   └── app.py              # FastAPI factory + SPA-раздача
├── webapp/                 # Mini App (React + TypeScript + Tailwind)
│   └── src/
│       ├── pages/          # Страницы: Home, Scan, Edit, Vote, Tip, Settle...
│       ├── components/     # UI-компоненты + bottom sheets
│       ├── api/            # HTTP-клиент + React Query хуки
│       ├── hooks/          # useTelegram, useWebSocket
│       └── lib/            # Утилиты (currency, resize)
├── alembic/                # Миграции БД
├── locales/                # Переводы (ru, en)
├── tools/                  # Скрипты обслуживания
└── tests/                  # Pytest (SQLite in-memory)
```

### Ключевые паттерны

- **Lazy init** — `get_settings()` и `get_async_session()` откладывают инициализацию; `.env` не нужен при импорте (важно для тестов)
- **DB через middleware** — `DbSessionMiddleware` внедряет `AsyncSession` в каждый хендлер бота
- **FSM** — `CheckStates` (фото → OCR → редактирование), `VotingStates` (кастомные чаевые)
- **Виртуальные сессии** — без групп Telegram; участники связаны через `invite_code` deep links
- **Админ = участник** — `create_session()` автоматически добавляет админа как участника
- **Quantity-aware голосование** — `cycle_vote()` инкрементирует количество (0→1→2→...→max→0)
- **Персональные чаевые** — каждый выбирает свой %, калькулятор применяет индивидуально
- **OCR-устойчивость** — regex-извлечение JSON, очистка спецтокенов LLM, мердж multi-photo
- **Real-time** — WebSocket для live-обновлений голосов, подтверждений, чаевых
- **UUID PK** на всех таблицах, `BigInteger` для Telegram user ID
- **selectin loading** — async-safe eager loading на всех one-to-many

---

## Модели базы данных

### Session

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | PK |
| `admin_tg_id` | BigInteger | Telegram ID создателя |
| `invite_code` | String(32) | Уникальный код приглашения |
| `status` | String(20) | `created` → `voting` → `closed` → `settled` |
| `currency` | String(8) | Валюта чека (default: `RUB`) |
| `tip_percent` | Integer | Глобальный % чаевых (fallback) |
| `created_at` | DateTime | Дата создания |
| `closed_at` | DateTime | Дата закрытия (nullable) |

### SessionItem

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | PK |
| `session_id` | UUID | FK → Session |
| `name` | String | Название блюда |
| `price` | Numeric(10,2) | Цена (за все quantity) |
| `quantity` | Integer | Количество порций |

### SessionMember

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | PK |
| `session_id` | UUID | FK → Session |
| `user_tg_id` | BigInteger | Telegram ID участника |
| `display_name` | String | Имя участника |
| `tip_percent` | Integer | Персональный % чаевых (nullable) |
| `confirmed` | Boolean | Подтвердил ли выбор |
| `joined_at` | DateTime | Дата присоединения |

### ItemVote

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | PK |
| `item_id` | UUID | FK → SessionItem |
| `user_tg_id` | BigInteger | Telegram ID голосующего |
| `quantity` | Integer | Сколько порций взял (1, 2, ...) |

### UserQuota

| Поле | Тип | Описание |
|------|-----|----------|
| `user_tg_id` | BigInteger | PK, Telegram ID |
| `free_scans_used` | Integer | Использовано бесплатных сканирований |
| `paid_scans` | Integer | Купленные сканирования |
| `quota_reset_at` | DateTime | Дата следующего сброса |

### Payment

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | PK |
| `user_tg_id` | BigInteger | Telegram ID плательщика |
| `session_id` | UUID | FK → Session (nullable) |
| `stars_amount` | Integer | Сумма в Telegram Stars |
| `telegram_charge_id` | String | ID транзакции Telegram |
| `created_at` | DateTime | Дата платежа |

---

## REST API

Все эндпоинты требуют авторизацию через заголовок `Authorization: tma <initData>`, где `initData` — данные из Telegram Mini App SDK, валидируемые через HMAC-SHA256.

### Сессии (`/api/sessions`)

| Метод | Путь | Доступ | Описание |
|-------|------|--------|----------|
| `POST` | `/api/sessions` | Любой | Создать сессию. Body: `{"currency": "RUB"}` |
| `GET` | `/api/sessions/my` | Любой | Список сессий пользователя |
| `GET` | `/api/sessions/{session_id}` | Участник | Детали сессии (items, members, votes) |
| `GET` | `/api/sessions/invite/{code}` | Любой | Найти сессию по invite-коду |
| `POST` | `/api/sessions/invite/{code}/join` | Любой | Присоединиться к сессии |
| `POST` | `/api/sessions/{id}/remind/{member_tg_id}` | Админ | Отправить напоминание участнику |
| `POST` | `/api/sessions/{id}/finish` | Админ | Закрыть голосование |
| `POST` | `/api/sessions/{id}/settle` | Админ | Рассчитать и зафиксировать итоги |
| `DELETE` | `/api/sessions/history` | Любой | Удалить свои settled-сессии |

### Голосование (`/api/sessions/{session_id}/...`)

| Метод | Путь | Body | Описание |
|-------|------|------|----------|
| `POST` | `.../vote` | `{"item_id": "...", "quantity": 2}` | Проголосовать / установить количество |
| `POST` | `.../tip` | `{"tip_percent": 15}` | Установить % чаевых |
| `POST` | `.../confirm` | — | Подтвердить выбор |
| `POST` | `.../unconfirm` | — | Отменить подтверждение |
| `GET` | `.../shares` | — | Получить расчёт для всех участников |
| `GET` | `.../my-share` | — | Получить свой расчёт |
| `POST` | `.../resolve-unvoted` | `{"decisions": {"item_id": "split"\|"remove"}}` | Обработать невыбранные блюда |

### OCR и позиции (`/api/sessions/{session_id}/...`)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `.../photos` | Загрузить фото (multipart/form-data) |
| `POST` | `.../ocr` | Запустить OCR (проверка квоты, WebSocket-прогресс) |
| `PUT` | `.../items` | Заменить все позиции. Body: `{"items": [...]}` |
| `PUT` | `.../items/{item_id}` | Обновить позицию. Body: `{"name": "...", "price": 500}` |
| `DELETE` | `.../items/{item_id}` | Удалить позицию |

### Квота (`/api/quota`)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/quota` | Информация о квоте: `{free_scans_left, paid_scans, reset_at}` |
| `POST` | `/api/quota/reset` | Сбросить счётчик бесплатных сканирований |

### WebSocket

```
ws://<host>/ws/{session_id}?token=<initData>
```

Подключение с авторизацией через query-параметр. Сервер отправляет JSON-события:

| Событие | Данные | Когда |
|---------|--------|-------|
| `vote_updated` | `{item_id, user_tg_id, quantity}` | Участник голосует |
| `member_joined` | `{user_tg_id, display_name}` | Новый участник |
| `member_confirmed` | `{user_tg_id}` | Подтверждение выбора |
| `member_unconfirmed` | `{user_tg_id}` | Отмена подтверждения |
| `tip_changed` | `{user_tg_id, tip_percent}` | Изменение чаевых |
| `session_status` | `{status}` | Админ закрыл голосование |
| `items_updated` | `{count}` | Обновление позиций |
| `ocr_progress` | `{current, total}` | Прогресс OCR (multi-photo) |

---

## Бот: команды и хендлеры

### Команды

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню + кнопка Mini App |
| `/start <invite_code>` | Deep link — присоединиться к сессии |

### Кнопки главного меню

| Кнопка | Действие |
|--------|----------|
| Разделить чек | Запрос фото чека |
| Моя квота | Показать лимиты сканирований |
| Помощь | Инструкция |

### Flow через бота

```
Фото чека → [OCR] → Подтверждение/Редактирование → QR + invite link
    → Участники присоединяются через deep link
    → Голосование (inline-кнопки с количеством)
    → Выбор чаевых (0/10/15/20/custom %)
    → Подтверждение → Админ видит прогресс
    → Завершение → Обработка невыбранных → Расчёт
    → Push-уведомления каждому с его суммой
```

### FSM-состояния

**CheckStates:**
- `collecting_photos` — приём фото чека
- `reviewing_ocr` — просмотр результатов OCR
- `editing_item` — редактирование отдельной позиции

**VotingStates:**
- `custom_tip` — ввод произвольного % чаевых

---

## Mini App (фронтенд)

React + TypeScript + Tailwind CSS + React Router + TanStack Query.

### Страницы

| Путь | Компонент | Описание |
|------|-----------|----------|
| `/` | HomePage | Главная: создание сессии, история |
| `/scan/:code` | ScanPage | Загрузка фото + OCR |
| `/session/:code/edit` | EditItemsPage | Редактирование позиций |
| `/session/:code/share` | ShareSessionPage | QR-код + invite-ссылка |
| `/session/:code/join` | JoinPage | Страница присоединения |
| `/session/:code/vote` | VotingPage | Голосование за блюда |
| `/session/:code/tip` | TipPage | Выбор чаевых + подтверждение |
| `/session/:code/admin` | VotingAdminPage | Прогресс голосования (для админа) |
| `/session/:code/unvoted` | UnvotedItemsPage | Невыбранные блюда |
| `/session/:code/settle` | SettlePage | Итоги расчёта |
| `/session/:code/history` | SessionHistoryPage | Просмотр завершённой сессии |
| `/quota` | PaymentQuotaPage | Покупка сканирований за Stars |

### Авторизация

Фронтенд передаёт `initData` из Telegram Mini App SDK в заголовке `Authorization: tma <initData>`. Бэкенд валидирует HMAC-SHA256 подпись с `BOT_TOKEN`.

### Real-time обновления

`useWebSocket(sessionId)` подключается к `/ws/{session_id}` и инвалидирует React Query кэш при получении событий. Голоса обновляются оптимистично через `useState`.

---

## Мультиязычность

Бот использует i18n aiogram (gettext + Babel). Локаль определяется из `User.language_code` в Telegram. Поддерживаются **ru** и **en**.

Добавление нового языка:
```bash
pybabel init -i locales/messages.pot -d locales -D messages -l uk
# Отредактировать locales/uk/LC_MESSAGES/messages.po
pybabel compile -d locales -D messages
```

Обновление переводов после изменения строк в коде:
```bash
pybabel extract -F babel.cfg -o locales/messages.pot .
pybabel update -d locales -D messages -i locales/messages.pot
# Отредактировать .po, затем:
pybabel compile -d locales -D messages
```

---

## Монетизация

Freemium-модель с оплатой через Telegram Stars:

- `FREE_SCANS_PER_MONTH` бесплатных сканирований в месяц (сбрасывается автоматически)
- После лимита — оплата через Stars (`SCAN_PRICE_STARS` за сканирование)
- Оплаченные сканы накапливаются и расходуются при следующих OCR-запросах
- Flow оплаты: invoice → pre-checkout → successful_payment → `grant_paid_scan()`

---

## Тесты

```bash
# Все тесты (SQLite in-memory, PostgreSQL не нужен)
uv run pytest

# Конкретный тест
uv run pytest tests/test_calculator.py::test_shared_dish -v

# С покрытием
uv run pytest --cov=bot --cov=api
```

Тесты используют `aiosqlite` и fixture `db_session` из `conftest.py`. Конфигурация lazy, поэтому `.env` не требуется.

---

## Линтинг

```bash
uv run ruff check bot/ api/ tests/
uv run ruff format bot/ api/ tests/
```

---

## Миграции БД

```bash
# Создать новую миграцию
uv run alembic revision --autogenerate -m "описание"

# Применить все миграции
uv run alembic upgrade head

# Откатить на одну миграцию
uv run alembic downgrade -1

# Показать текущую версию
uv run alembic current
```

История миграций:
1. `bea57eb4c49e` — начальные таблицы (sessions, items, members, votes, photos, quotas, payments)
2. `156dac2499c0` — `tip_percent` и `confirmed` в session_members
3. `254284816472` — `paid_scans` в user_quotas
4. `4eb5c3f19b63` — `quantity` в item_votes
5. `5a1b2c3d4e5f` — `currency` в sessions

---

## Утилиты обслуживания

### Скрипт `tools/db_cleanup.sh`

Работа с данными в БД через `docker compose exec db psql`:

```bash
# Сбросить счётчик бесплатных сканирований (всем или конкретному)
./tools/db_cleanup.sh reset-quota [USER_TG_ID]

# Удалить завершённые (settled) сессии
./tools/db_cleanup.sh clear-history [USER_TG_ID]

# Удалить ВСЕ сессии
./tools/db_cleanup.sh clear-all [USER_TG_ID]

# Показать квоты пользователей
./tools/db_cleanup.sh show-quotas

# Показать последние сессии
./tools/db_cleanup.sh show-sessions
```

Переменная `PSQL_CMD` переопределяет команду подключения к БД (по умолчанию `docker compose exec -T db psql -U user -d checksplitter`).

---

## Логирование

Все хендлеры бота и API-маршруты логируют `user_id` и контекст действия:

```
INFO bot.handlers.start: user_id=123456 /start
INFO bot.handlers.check: user_id=123456 OCR start
INFO api.routes.voting: user_id=123456 vote session=abc item=def qty=2
INFO bot.services.ocr: OCR: processing photo 1/2
```

Уровень логирования: `INFO` (настраивается в `bot/__main__.py`).

---

## Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Telegram Bot | aiogram 3.x (long polling) |
| REST API | FastAPI + uvicorn |
| WebSocket | FastAPI WebSocket + ConnectionManager |
| ORM | SQLAlchemy 2.x (async + asyncpg) |
| Миграции | Alembic |
| OCR | OpenRouter API (LLM с vision) |
| БД | PostgreSQL 17 |
| Фронтенд | React 18 + TypeScript + Tailwind CSS |
| Роутинг | React Router 6 |
| Data fetching | TanStack Query (React Query) |
| QR-коды | qrcode (Python) + qrcode.react (JS) |
| i18n | gettext + Babel |
| Контейнеризация | Docker multi-stage + Docker Compose |
| Пакеты (Python) | uv |
| Линтер | Ruff |
| Тесты | pytest + pytest-asyncio + aiosqlite |
