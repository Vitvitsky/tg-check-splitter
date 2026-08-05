# Разделение бота и API + пакет `core` — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Развести бота и API по разным контейнерам, чтобы падение одного не роняло другого, и вынести общее ядро в пакет `core/`.

**Architecture:** `bot/` сегодня — это общее ядро (конфиг, БД, модели, сервисы) плюс aiogram-хендлеры; `api/` импортирует из него 40 раз, обратных импортов нет. Разрезаем ровно по границе «тянет ли файл aiogram» — она уже существует в коде и совпадает с бот-специфичностью один в один. Затем поднимаем три сервиса из одного образа: одноразовый `migrate`, `api` и `bot`, где последние два зависят от `migrate` и не зависят друг от друга.

**Tech Stack:** Python 3.12, uv, SQLAlchemy 2 + asyncpg, Alembic, FastAPI, aiogram 3, ruff, pytest, Docker Compose.

**Спек:** `docs/superpowers/specs/2026-08-05-split-bot-api-design.md`

## Global Constraints

- Пакет проекта **не устанавливается** (`uv sync --frozen --no-dev --no-install-project`), модули берутся из рабочей директории. `pyproject.toml` править не нужно.
- `ruff`: `line-length = 99`, `target-version = "py312"`.
- `pytest`: `asyncio_mode = "auto"`, `testpaths = ["tests"]`.
- В образе `python:3.12-slim` **нет `curl`** (проверено). Любая проба — через stdlib `urllib`.
- Порт API остаётся **8005**: `nginx/tg-check-splitter.conf` и его `upstream` не трогаем.
- Все перемещения файлов — через `git mv`, чтобы не оборвать историю (в `services/session.py` живут блокировки и расчёт денег).
- Тесты конкурентности молча пропускаются без `TEST_DATABASE_URL`. Любое утверждение «тесты прошли» без проверки, что они **исполнились**, недействительно.
- Два коммита, не один: сначала `core/`, отдельно топология.

---

## File Structure

**Создаются:**

| Путь | Ответственность |
|---|---|
| `core/__init__.py` | пустой маркер пакета |
| `core/config.py` | ← `bot/config.py`, настройки pydantic |
| `core/db.py` | ← `bot/db.py`, движок и сессии |
| `core/utils.py` | ← `bot/utils.py`, форматирование денег |
| `core/models/` | ← `bot/models/`, ORM-модели |
| `core/services/` | ← `bot/services/`, доменные сервисы |

**Изменяются:**

| Путь | Что |
|---|---|
| `api/**/*.py` (14 файлов) | префиксы импортов |
| `bot/**/*.py` (5 файлов) | префиксы импортов |
| `tests/**/*.py` (20 файлов) | префиксы импортов |
| `alembic/env.py:9-10` | `from bot.config`, `from bot.models` |
| `Dockerfile` | `COPY core/ core/`; снять `CMD` |
| `docker-compose.yml` | три сервиса вместо `app` |
| `CLAUDE.md` | команды ruff, имена контейнеров |
| `README.md:63,68` | таблица сервисов, описание сборки |

**Удаляется:** `entrypoint.sh`.

**Остаётся в `bot/`:** `__main__.py`, `handlers/`, `keyboards/`, `i18n.py`, `middlewares.py` — ровно файлы, тянущие aiogram.

---

### Task 1: Выделить пакет `core`

**Files:**
- Create: `core/__init__.py`
- Move: `bot/config.py`, `bot/db.py`, `bot/utils.py`, `bot/models/`, `bot/services/` → `core/`
- Modify: `api/**/*.py`, `bot/**/*.py`, `tests/**/*.py`, `alembic/env.py`, `Dockerfile`
- Test: весь существующий набор (226 тестов), новых тестов не пишем

**Interfaces:**
- Consumes: ничего (первая задача).
- Produces: пакет `core` с публичными именами, неизменными по сигнатурам — меняется только путь импорта:
  - `core.config.get_settings() -> Settings`
  - `core.db.get_engine()`, `core.db.get_async_session()`
  - `core.utils.format_price(amount: Decimal | int | float, currency: str = "RUB") -> str`
  - `core.models.Base`, `core.models.{ItemVote, Payment, Session, SessionItem, SessionMember, SessionPhoto, UserQuota}`
  - `core.services.session.SessionService`, `core.services.quota.QuotaService`, `core.services.ocr.OcrService`, `core.services.calculator.calculate_shares`, `core.services.calculator.calculate_user_share`

Это чистый рефакторинг: поведение не меняется, поэтому «падающий тест» писать не на что. Роль красной фазы играет **зафиксированный до правки базовый прогон** — без него утверждение «ничего не сломалось» непроверяемо.

- [ ] **Шаг 1: Поднять тестовую БД и создать базу для гонок**

```bash
docker compose up -d db
docker exec tg-check-splitter-db-1 psql -U user -d postgres -c "CREATE DATABASE racetest;" || true
```

Команда `CREATE DATABASE` упадёт, если база уже есть — это нормально, поэтому `|| true`.

- [ ] **Шаг 2: Снять базовый прогон и убедиться, что тесты конкурентности ИСПОЛНИЛИСЬ**

```bash
TEST_DATABASE_URL=postgresql+asyncpg://user:password@127.0.0.1:5433/racetest \
  uv run pytest tests/test_concurrency.py -v
```

Ожидается: строки `PASSED`. **Если видите `SKIPPED` — остановитесь**: переменная не подхватилась, и дальше вся проверка бессмысленна, потому что переезжает именно тот код, который эти тесты стерегут.

- [ ] **Шаг 3: Снять базовый прогон всего набора и записать число**

```bash
TEST_DATABASE_URL=postgresql+asyncpg://user:password@127.0.0.1:5433/racetest \
  uv run pytest -q | tail -3
```

Запишите итоговое число прошедших тестов. Оно должно совпасть после переезда.

- [ ] **Шаг 4: Перенести файлы через `git mv`**

```bash
mkdir -p core
git mv bot/config.py   core/config.py
git mv bot/db.py       core/db.py
git mv bot/utils.py    core/utils.py
git mv bot/models      core/models
git mv bot/services    core/services
: > core/__init__.py
git add core/__init__.py
```

`bot/__init__.py` **остаётся на месте** — пакет `bot` продолжает существовать.

- [ ] **Шаг 5: Переписать префиксы импортов**

Переезжают ровно пять имён. Оставшиеся (`bot.handlers`, `bot.keyboards`, `bot.i18n`, `bot.middlewares`) под шаблон не попадают, поэтому замена безопасна:

```bash
grep -rlE 'bot\.(config|db|utils|models|services)' api bot tests alembic --include='*.py' \
  | xargs sed -i -E 's/\bbot\.(config|db|utils|models|services)\b/core.\1/g'
```

- [ ] **Шаг 6: Проверить, что `alembic/env.py` действительно переписан**

```bash
grep -n "^from" alembic/env.py
```

Ожидается `from core.config import get_settings` и `from core.models import Base`. Если там остался `bot.` — автогенерация увидит пустую схему и предложит удалить все таблицы.

- [ ] **Шаг 7: Убедиться, что живых ссылок на переехавшие модули не осталось**

```bash
grep -rnE '\bbot\.(config|db|utils|models|services)\b' api bot tests alembic --include='*.py' \
  && echo "ОСТАЛИСЬ ССЫЛКИ — чинить" || echo "чисто"
```

Ожидается `чисто`.

- [ ] **Шаг 8: Добавить `core/` в `Dockerfile`**

Рядом со строкой `COPY bot/ bot/` добавить строку выше:

```dockerfile
COPY core/ core/
COPY bot/ bot/
COPY api/ api/
```

- [ ] **Шаг 9: Линт**

```bash
uv run ruff check core/ bot/ api/ tests/ && uv run ruff format core/ bot/ api/ tests/
```

Ожидается: без ошибок. Осиротевший импорт всплывёт здесь.

- [ ] **Шаг 10: Полный прогон — число должно совпасть с шагом 3**

```bash
TEST_DATABASE_URL=postgresql+asyncpg://user:password@127.0.0.1:5433/racetest \
  uv run pytest -q | tail -3
```

- [ ] **Шаг 11: Проверить изоляцию окружения**

```bash
FREE_SCANS_PER_MONTH=99 uv run pytest -q | tail -3
```

Ожидается: проходит. Это ловушка из `CLAUDE.md` — тесты не должны читать локальный `.env`.

- [ ] **Шаг 12: Убедиться, что Alembic по-прежнему видит модели**

```bash
uv run alembic revision --autogenerate -m "should-be-empty"
```

Открыть созданный файл в `alembic/versions/`. Тело `upgrade()` обязано быть пустым (`pass`). **Непустое — значит `target_metadata` потеряла модели, чинить шаг 6.** После проверки файл удалить:

```bash
rm alembic/versions/*should_be_empty*.py
```

- [ ] **Шаг 13: Проверить, что образ собирается**

```bash
docker compose build app
```

- [ ] **Шаг 14: Коммит**

```bash
git add -A
git commit -m "refactor: вынести общее ядро из bot/ в core/

api/ импортировал из пакета bot/ 40 раз, обратных импортов не было ни одного:
там лежат модели, БД, конфиг и сервисы, а не бот. Граница проведена по признаку
«тянет ли файл aiogram» — множество таких файлов точно совпало с множеством
бот-специфичных, пересечения нет.

core/ получает config, db, utils, models, services; bot/ остаётся с __main__,
handlers, keyboards, i18n, middlewares.

Поведение не меняется. python -m bot остаётся валидным, поэтому entrypoint.sh
продолжает работать и коммит разворачивается отдельно от смены топологии."
```

---

### Task 2: Развести на три сервиса

**Files:**
- Modify: `docker-compose.yml`, `Dockerfile`, `CLAUDE.md`, `README.md`
- Delete: `entrypoint.sh`
- Test: приёмка вручную (см. шаги 4–6)

**Interfaces:**
- Consumes: пакет `core` из Task 1; `python -m bot` и `api.app:create_app` как точки входа.
- Produces: сервисы `migrate`, `api`, `bot`. Контейнеры называются `tg-check-splitter-migrate-1`, `-api-1`, `-bot-1`. Контейнера `tg-check-splitter-app-1` больше нет.

- [ ] **Шаг 1: Переписать `docker-compose.yml`**

Якорь `&app-base` убирает тройное дублирование сборки и окружения:

```yaml
x-app-base: &app-base
  build: .
  image: tg-check-splitter-app
  env_file: .env
  environment:
    DATABASE_URL: postgresql+asyncpg://user:password@db:5432/checksplitter

services:
  migrate:
    <<: *app-base
    command: ["uv", "run", "alembic", "upgrade", "head"]
    restart: "no"
    depends_on:
      db:
        condition: service_healthy

  api:
    <<: *app-base
    command: ["uv", "run", "uvicorn", "api.app:create_app",
              "--factory", "--host", "0.0.0.0", "--port", "8005"]
    ports:
      - "8005:8005"
    healthcheck:
      # curl в python:3.12-slim нет — проба через stdlib urllib.
      test: ["CMD", "python", "-c",
             "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8005/api/health').read()"]
      interval: 10s
      timeout: 3s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    depends_on:
      migrate:
        condition: service_completed_successfully

  bot:
    <<: *app-base
    command: ["uv", "run", "python", "-m", "bot"]
    restart: unless-stopped
    depends_on:
      migrate:
        condition: service_completed_successfully

  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: checksplitter
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d checksplitter"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
```

`api` и `bot` зависят от `migrate`, но **не друг от друга** — это и есть суть задачи.

- [ ] **Шаг 2: Убрать `entrypoint.sh` и `CMD`**

```bash
git rm entrypoint.sh
```

Из `Dockerfile` удалить три последние строки:

```dockerfile
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
```

`CMD` не нужен: каждый сервис задаёт свой `command`.

- [ ] **Шаг 3: Собрать и поднять**

```bash
docker compose up -d --build
```

- [ ] **Шаг 4: Проверить, что все трое в ожидаемом состоянии**

```bash
docker compose ps -a
```

Ожидается: `migrate` — `Exited (0)`; `api` — `Up (healthy)`; `bot` — `Up`. Если `api` застрял в `health: starting` дольше минуты, смотреть `docker compose logs api`.

- [ ] **Шаг 5: Приёмка — падение бота не трогает API**

```bash
docker compose kill bot
curl -fsS http://127.0.0.1:8005/api/health && echo " ← API жив"
sleep 15 && docker compose ps bot
```

Ожидается: `/api/health` отвечает, `bot` поднялся сам (`restart: unless-stopped`). **До этой правки первая команда убила бы и API** — в этом весь смысл задачи.

- [ ] **Шаг 6: Приёмка в обратную сторону**

```bash
docker compose kill api
sleep 5 && docker compose ps bot
```

Ожидается: `bot` — `Up`, не перезапускался из-за смерти соседа. Затем вернуть всё:

```bash
docker compose up -d
```

- [ ] **Шаг 7: Обновить `CLAUDE.md` — команда линта**

В разделе `## Commands` заменить строку

```
uv run ruff check bot/ api/ tests/ && uv run ruff format bot/ api/ tests/
```

на

```
uv run ruff check core/ bot/ api/ tests/ && uv run ruff format core/ bot/ api/ tests/
```

- [ ] **Шаг 8: Обновить `CLAUDE.md` — имена контейнеров**

В разделе `## Debugging the Mini App without a console`, строка 279 — единственное вхождение старого имени. Заменить `tg-check-splitter-app-1` на `tg-check-splitter-api-1`:

```bash
docker logs tg-check-splitter-api-1 2>&1 | grep -E 'POST /api/sessions/[^ ]+/(vote|tip|confirm)'
```

Соседнюю команду с `tg-check-splitter-db-1` **не трогать** — имя контейнера БД не меняется.

Добавить после блока:

```markdown
The bot and the API are separate services now, so `docker compose logs bot` and
`docker compose logs api` are separate too — a Mini App bug never has to be read out of
polling noise.
```

В разделе `## Deployment notes` заменить абзац на строках 316–318 (`entrypoint.sh` … `wait -n` … `splitting them is backlog item F`) на:

```markdown
Three services from one image: `migrate` (one-shot, `alembic upgrade head`), `api` and
`bot`. Both depend on `migrate` completing and on nothing else — killing one does not
touch the other. There is no `entrypoint.sh` any more; each service carries its own
`command`.
```

Команду пересборки на строке 321 поправить с `docker compose up -d --build app` на `docker compose up -d --build api`.

Обратите внимание: этот абзац про вшитый в образ фронтенд остаётся верным — фронтенд по-прежнему собирается в образ и отдаётся сервисом `api`.

- [ ] **Шаг 9: Обновить `README.md`**

Строку 63 («Multi-stage сборка… запускает бота и API в одном контейнере. Entrypoint автоматически применяет миграции.») заменить на:

```markdown
Multi-stage сборка: Node.js собирает фронтенд, Python-образ обслуживает три сервиса.
Миграции применяет отдельный одноразовый сервис `migrate`, после него независимо
стартуют `api` и `bot`.
```

Таблицу сервисов заменить на:

```markdown
| Сервис    | Порт | Описание |
|-----------|------|----------|
| `migrate` | —    | Одноразовый: `alembic upgrade head`, затем выходит |
| `api`     | 8005 | REST, WebSocket, Mini App |
| `bot`     | —    | Telegram-бот, polling |
| `db`      | 5433 | PostgreSQL 17 |
```

- [ ] **Шаг 10: Обновить бэклог**

В `docs/BACKLOG.md`, пункт F, у подпункта **F1** заменить строку статуса на:

```markdown
**Сделано 2026-08-05.** См. `docs/superpowers/plans/2026-08-05-split-bot-api.md`.
```

F2 (Rust) остаётся нетронутым.

- [ ] **Шаг 11: Коммит**

```bash
git add -A
git commit -m "refactor: развести бота и API по отдельным сервисам

entrypoint.sh поднимал оба процесса и делал wait -n, поэтому падение любого
роняло контейнер целиком: упавший polling бота гасил и Mini App.

Теперь три сервиса из одного образа: migrate одноразовым применяет миграции,
api и bot зависят от него и не зависят друг от друга. entrypoint.sh удалён,
CMD снят — каждый сервис несёт свой command.

Контейнер tg-check-splitter-app-1 исчез; появились -migrate-1, -api-1, -bot-1.
Рецепты отладки в CLAUDE.md и таблица сервисов в README обновлены под новые имена.

Приёмка: docker compose kill bot не влияет на /api/health, бот поднимается сам."
```

---

## Замечания для исполнителя

**Порт 8005 и nginx.** Наружу по-прежнему смотрит `api` на 8005, `nginx/tg-check-splitter.conf` менять не нужно. Если после разворота сайт отдаёт 502 — проверяйте `docker compose ps api`, а не конфиг nginx.

**Почему `migrate` с `restart: "no"`.** С `unless-stopped` сервис, штатно завершившийся кодом 0, уходил бы в бесконечный цикл перезапусков, а `service_completed_successfully` никогда бы не сработал.

**`docker compose ps` без `-a` не покажет `migrate`** — он уже вышел. Для проверки нужен `-a`.

**Если Task 1 уже развёрнут на бою, а Task 2 ещё нет** — это рабочее состояние: `entrypoint.sh` продолжает поднимать оба процесса, `python -m bot` остался валидным.
