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
# Отредактировать .env: BOT_TOKEN, ZAI_API_KEY, DATABASE_URL

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

Multi-stage сборка: Node.js собирает фронтенд, Python-образ обслуживает три сервиса.
Миграции применяет отдельный одноразовый сервис `migrate`, после него независимо
стартуют `api` и `bot`.

| Сервис    | Порт | Описание |
|-----------|------|----------|
| `migrate` | —    | Одноразовый: `alembic upgrade head`, затем выходит |
| `api`     | 8005 | REST, WebSocket, Mini App |
| `bot`     | —    | Telegram-бот, polling |
| `db`      | 5433 | PostgreSQL 17 |

---

## Переменные окружения

| Переменная | Тип | По умолчанию | Описание |
|---|---|---|---|
| `BOT_TOKEN` | str | — | Токен от [@BotFather](https://t.me/BotFather) |
| `ZAI_API_KEY` | str | — | API-ключ [Z.AI](https://z.ai) |
| `ZAI_MODEL` | str | `glm-4.6v` | Vision-модель для OCR |
| `DATABASE_URL` | str | — | PostgreSQL URL (`postgresql+asyncpg://user:password@localhost:5433/checksplitter`) |
| `WEBAPP_URL` | str | `http://localhost:5173` | Базовый URL Mini App |
| `FREE_SCANS_PER_MONTH` | int | `3` | Лимит бесплатных сканирований в месяц |
| `SCAN_PRICE_STARS` | int | `1` | Цена платного сканирования в Telegram Stars |
| `DB_POOL_SIZE` | int | `20` | Соединений в пуле. Дефолт SQLAlchemy (5) упирал API в ~25 req/s: соединение стоит ~80 мс, запрос — 0.19 мс |
| `DB_MAX_OVERFLOW` | int | `10` | Сверх пула на всплесках. Сумма с `DB_POOL_SIZE` должна оставаться заметно ниже `max_connections` Postgres (100) |

---

## Архитектура

```
tg-check-splitter/
├── bot/                    # Telegram-бот (aiogram 3.x) — тонкий слой, см. ниже
│   ├── handlers/           # Роутеры: start (вход в Mini App), payment (Stars)
│   ├── services/           # Бизнес-логика: ocr, session, calculator, quota
│   ├── models/             # SQLAlchemy ORM-модели
│   ├── keyboards/          # Клавиатуры: главное меню + кнопка Mini App
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

### Разделение обязанностей: Mini App главный, бот тонкий

Весь продуктовый флоу — сканирование, редактирование, голосование, чаевые, расчёт —
живёт в Mini App и REST API. Бот делает ровно три вещи: приветствие, передачу
инвайта в Mini App и приём платежей Stars (Telegram доставляет обновления об оплате
только через бота).

Так было не всегда. `bot/handlers/{check,voting,admin}.py` реализовывали тот же флоу
на FSM и inline-кнопках — вторую копию логики поверх той же БД. Стык между копиями
был рваный: QR вёл в чат с ботом, бот присоединял участника и слал кнопку с
`?startapp=`, который фронтенд никогда не читал, — участник оказывался на главной
вместо своего чека. Копия удалена; при добавлении фич не воссоздавайте её.

### Ключевые паттерны

- **Lazy init** — `get_settings()` и `get_async_session()` откладывают инициализацию; `.env` не нужен при импорте (важно для тестов)
- **DB через middleware** — `DbSessionMiddleware` внедряет `AsyncSession` в каждый хендлер бота
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

### Хранение фото чеков

Байты лежат в `session_photos.data` (`BYTEA`, nullable, **deferred**). Раньше они
хранились в словаре в памяти процесса: рестарт обрывал все активные сессии, второй воркер
запустить было нельзя, и словарь рос бесконечно.

Отдельная уборка не нужна — фото живут минуты, от загрузки до успешного OCR:

- `clear_photo_bytes()` обнуляет колонку сразу после удачного распознавания — сюда
  уходит практически весь объём, устойчивое состояние близко к нулю;
- `session_photos.session_id` каскадный, так что всё, что до OCR не дошло, умирает
  вместе с сессией.

При **неудачном** OCR байты намеренно сохраняются: скан возвращён, попытку можно
повторить.

`deferred` обязателен: `Session.photos` грузится через `selectin`, и без него каждый
`GET /api/sessions/{id}` тащил бы JPEG'и. Читать только через
`SessionService.get_photo_bytes()`, не через атрибут `photo.data`.

Объём: клиент ужимает до 2048 px (0.3–1 МБ), сервер ограничивает фото 5 МБ и чек —
пятью фото. Худший случай 25 МБ на сессию, реальный — 1–3 МБ.

### Расчёт: один раз, дальше сессия заморожена

`POST /settle` начинается с `claim_settlement()` — условного
`UPDATE ... WHERE status <> 'settled'`. Ровно один вызов получает `True` и рассылает
пуши; повторные пересчитывают те же суммы и молча их возвращают. Раньше каждый вызов
заново сообщал всему столу их доли.

Суммы намеренно **не сохраняются** — и не нужно. Расчёт закрывает сессию на изменения:
`_require_open()` в `api/routes/voting.py` и `must_be_open` в `api/routes/ocr.py`
отвечают `409 session_settled` на голоса, чаевые, подтверждения и правку позиций.
Входные данные заморожены, поэтому пересчёт на чтении даёт тот же ответ всегда.

Уберёте эти проверки — исчезнет и идемпотентность: доли считаются на чтении, и поздний
голос начнёт молча расходиться с суммой, уже отправленной людям в пуш.

Чтение (`/shares`, `/my-share`) после расчёта остаётся открытым. `closed_at` наконец
заполняется — колонка была в модели и никогда не записывалась.

### Правила целостности

Заданы в `bot/models/` и в миграции `f1a2b3c4d5e6`; и то и другое обязательно —
ORM-каскад держит согласованной сессию SQLAlchemy, `ON DELETE` в БД покрывает
массовые удаления мимо ORM.

| Ограничение | Зачем |
|-------------|-------|
| `sessions → photos/items/members` `ON DELETE CASCADE` | Удаление сессии раньше падало с `IntegrityError` |
| `session_items → item_votes` `ON DELETE CASCADE` | Удаление блюда с голосами падало |
| `payments.session_id` `ON DELETE SET NULL` | Платёж — финансовая запись, переживает удаление сессии |
| `uq_session_members_session_user` | Гонка при join создавала дубль, и `get_member()` навсегда падал с `MultipleResultsFound` |
| `uq_item_votes_item_user` | То же для двойного тапа по блюду |
| `uq_payments_charge_id` | Telegram переотправляет `successful_payment`; без этого сканы начислялись дважды |

Вставки, которые могут проиграть гонку (`join_session`, `cycle_vote`, `set_vote`,
`add_vote_all`), ловят `IntegrityError`, откатываются и возвращают фактическое
состояние — гонка не должна превращаться в 500.

### Одновременный выбор одного блюда

Уникальные индексы защищают от дубля **одного** пользователя. Инвариант «заявлено ≤
количества блюда» **между разными** пользователями они не покрывают: все пути заявки
сначала читают заявленную сумму, потом пишут, и при READ COMMITTED двое, тапнувшие
последнюю порцию одновременно, оба видят «свободно» и оба вставляют.

Поэтому `cycle_vote`, `set_vote`, `add_vote_all` и `split_remaining_equally`
начинаются с `_lock_item()` — `SELECT … FOR UPDATE` на строке блюда. Заявки на одно
блюдо сериализуются; блокировка держится одну короткую транзакцию и конфликтует
только с заявками на то же блюдо.

`split_remaining_equally` раздаёт всем участникам в **одной** транзакции: коммит
в середине снял бы блокировку и снова открыл окно.

Проверяется в `tests/test_concurrency.py` — нужен настоящий PostgreSQL, на SQLite
эта гонка невоспроизводима:

```bash
docker compose up -d db
docker exec tg-check-splitter-db-1 psql -U user -d postgres -c "CREATE DATABASE racetest;"
TEST_DATABASE_URL=postgresql+asyncpg://user:password@127.0.0.1:5433/racetest uv run pytest tests/test_concurrency.py
```

Без `TEST_DATABASE_URL` эти тесты молча пропускаются.

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
| `POST` | `/api/sessions/{id}/settle` | Админ | Рассчитать и зафиксировать итоги. Идемпотентен |
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
| `POST` | `.../photos` | Загрузить фото (multipart/form-data), не более 5 на чек |
| `POST` | `.../ocr` | Запустить OCR (проверка квоты, WebSocket-прогресс) |

`POST .../ocr` отвечает `402` (квота исчерпана), `400` (нет фото / их больше пяти),
`422` (чек не распознан), `502` (провайдер недоступен), `504` (не уложились в дедлайн).
**На всех кодах, кроме 402 и 200, скан возвращается пользователю** — платят за
распознанный чек, а не за попытку. `use_scan()` возвращает корзину списания
(`free`/`paid`), чтобы `refund_scan()` вернул скан именно туда; иначе платный скан
тихо превращается в бесплатный.

Фото уходят в LLM параллельно, а весь вызов обёрнут в
`asyncio.timeout(_OCR_DEADLINE_SECONDS)` — 240 с против 300 с `proxy_read_timeout`
в nginx. Порядок важен: после таймаута nginx соединение уже разорвано и возвращать
квоту некому, поэтому приложение обязано упасть первым. Раньше фото обрабатывались
последовательно по 120 с, и чек из трёх фото гарантированно ловил 504 при уже
списанном скане.
| `PUT` | `.../items` | Заменить все позиции. Body: `{"items": [...]}` |
| `PUT` | `.../items/{item_id}` | Обновить позицию. Body: `{"name": "...", "price": 500}` |
| `DELETE` | `.../items/{item_id}` | Удалить позицию |

### Квота (`/api/quota`)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/quota` | Информация о квоте: `{free_scans_left, paid_scans, reset_at}` |
| `POST` | `/api/quota/invoice` | Создать Stars-инвойс. Body: `{"scans": 5}` → `{invoice_link}` |

Цена пака задаётся сервером (`SCAN_PACKS` в `api/routes/quota.py`), клиент называет
только размер пака. Mini App открывает ссылку через `openInvoice()`; зачисление
происходит в `bot/handlers/payment.py`, куда Telegram присылает обновления об оплате.

> `POST /api/quota/reset` удалён. Он обнулял счётчик бесплатных сканирований
> вызывающему без единой проверки — платный тариф обходился одним curl.
> Квота сбрасывается только на месячной границе, в `QuotaService`.

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

Бот не содержит продуктовой логики и не имеет FSM — он только открывает Mini App
и обслуживает платежи. См. «Разделение обязанностей» выше.

### Команды

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню + кнопка Mini App |
| `/start <invite_code>` | Legacy deep link: присоединяет и открывает Mini App |

### Кнопки главного меню

| Кнопка | Действие |
|--------|----------|
| Разделить чек | Открыть Mini App на экране сканирования |
| Моя квота | Показать лимиты сканирований |
| Помощь | Инструкция |

Фото, отправленное в чат, больше не запускает OCR — бот отвечает кнопкой в Mini App.

### Приглашения: две формы ссылок

| Ссылка | Кто генерирует | Что происходит |
|--------|----------------|----------------|
| `t.me/<bot>?startapp=<code>` | QR и Share в Mini App | Открывает Mini App; `useStartParam` роутит на `/session/<code>` |
| `t.me/<bot>?start=<code>` | старые, уже разосланные | Бот присоединяет и даёт кнопку в Mini App |
| `<WEBAPP_URL>/session/<code>/…` | кнопки в push-уведомлениях | Прямой маршрут; работает благодаря SPA-fallback |

`?startapp=` доставляет код через `start_param`, вне пути — путь всегда `/`.
Поэтому `useStartParam` срабатывает только в корне и не конфликтует с прямыми ссылками.

### Flow

```
Mini App: фото → OCR → редактирование → QR / invite link
    → участники открывают Mini App по ?startapp= и присоединяются
    → голосование с количеством → свой % чаевых → личная сводка → подтверждение
    → админ видит прогресс → завершение → обработка невыбранных → расчёт
    → бот шлёт каждому push с его суммой
```

---

## Mini App (фронтенд)

React + TypeScript + Tailwind CSS + React Router + TanStack Query.

### Маршруты и входы

Каждый маршрут должен иметь вход, иначе экран — сирота. `/quota` был именно таким:
покупка сканов работала от начала до конца, но открыть её было нельзя.

```
/ HomePage
├─ /scan ──────────► /session/:code/edit ──► /session/:code/vote
│                       └─ QR-модалка            ├─► /admin ──► /settle ──► /unvoted ─┐
│                          (приглашение)         │      └─► /share                    │
│                                                └─► /tip ───► /settle ◄──────────────┘
├─ /quota   карточка остатка сканов на главной; кнопка при 402 в ScanPage
├─ /session/:code/{edit|vote|settle|history}   по статусу сессии
│                       └─ history ──► /share
└─ /session/:code  JoinPage ──► /vote    вход только извне: ?startapp= и ссылки бота
```

Проверить после добавления страницы или ссылки:

```bash
cd webapp/src
grep -oE 'path="[^"]+"' App.tsx                                     # объявлено
grep -rhoE 'navigate\(`[^`]+`' pages components                     # достижимо
```

Страницы принимают `:code` (invite-код) и резолвят его в `session.id` через
`useSession(code)` до вызова хуков, которым нужен UUID (`useShares`, `useVote`,
`useWebSocket`). Передать код напрямую — главная ловушка этой схемы; сейчас все
страницы делают это правильно.

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

### Внешние ключи в тестах включены принудительно

SQLite игнорирует внешние ключи, пока для соединения не выполнен
`PRAGMA foreign_keys=ON`. Из-за этого набор тестов молча принимал удаления, которые
PostgreSQL отвергает: отсутствующие правила `ON DELETE` на sessions/items уехали в
прод при 109 зелёных тестах, а `DELETE /api/sessions/history` падал там **всегда**.

Поэтому все тестовые движки создаются через `make_test_engine()` из `tests/db.py`,
который ставит прагму на каждое соединение. Не создавайте `create_async_engine`
в тестах напрямую — иначе этот класс багов снова станет невидимым.

Схему миграций SQLite не проверяет вовсе: миграции написаны под PostgreSQL
(в `f1a2b3c4d5e6` используются `ctid` и `DELETE … USING`). Изменения, затрагивающие
DDL, прогоняйте на настоящей базе:

```bash
docker compose up -d db
docker exec tg-check-splitter-db-1 psql -U user -d postgres -c "CREATE DATABASE migtest;"
DATABASE_URL="postgresql+asyncpg://user:password@127.0.0.1:5433/migtest" uv run alembic upgrade head
```

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

### Скрипт `tools/stats.sh`

Статистика по боту из существующих данных — отдельного хранилища событий нет.

```bash
./tools/stats.sh mau        # DAU / WAU / MAU и липкость
./tools/stats.sh dau 30     # активные пользователи по дням
./tools/stats.sh funnel     # воронка: сессия -> фото -> распознано -> голоса -> расчёт
./tools/stats.sh retention  # возврат по месячным когортам
./tools/stats.sh money      # платежи и упирающиеся в лимит
./tools/stats.sh health     # размеры таблиц, объём неочищенных фото
./tools/stats.sh all
```

Активность = фактическое действие (создал сессию, присоединился, проголосовал,
заплатил), а не открытие приложения. Собирается объединением `sessions`,
`session_members`, `item_votes` и `payments`.

> Цифры за прошлое **не воспроизводятся задним числом**: `DELETE /api/sessions/history`
> удаляет рассчитанные сессии вместе с голосами, а с ними исчезает и свидетельство
> активности. Если статистика начнёт влиять на решения — нужна таблица `user_activity`,
> см. `docs/BACKLOG.md`, пункт B.

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
