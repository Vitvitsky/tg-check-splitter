# Check Splitter Bot

Telegram-бот для разделения ресторанного счёта между участниками.

## Как это работает

1. **Сканирование** — отправьте фото чека, LLM распознает позиции
2. **Редактирование** — проверьте и при необходимости исправьте список блюд
3. **Приглашение** — покажите QR-код или отправьте ссылку участникам ужина
4. **Голосование** — каждый участник отмечает свои блюда (с поддержкой количества: 1/2, 2/2)
5. **Чаевые** — каждый выбирает свой процент чаевых и видит личную сводку
6. **Расчёт** — бот показывает итоги с индивидуальными суммами

## Быстрый старт

### Требования

- Python 3.12+
- PostgreSQL (через Docker)
- [uv](https://docs.astral.sh/uv/) — менеджер пакетов

### Установка

```bash
# Клонировать и установить зависимости
git clone <repo-url>
cd tg-check-splitter
uv sync --extra dev

# Скопировать и заполнить .env
cp .env.example .env
# Отредактировать .env: BOT_TOKEN, OPENROUTER_API_KEY, DATABASE_URL

# Запустить PostgreSQL
docker compose up -d

# Применить миграции
uv run alembic upgrade head

# Запустить бота
uv run python -m bot
```

### Настройка .env

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен от [@BotFather](https://t.me/BotFather) |
| `OPENROUTER_API_KEY` | API-ключ [OpenRouter](https://openrouter.ai) |
| `OPENROUTER_MODEL` | Модель с поддержкой vision (например `google/gemini-2.0-flash-001`) |
| `DATABASE_URL` | PostgreSQL URL (`postgresql+asyncpg://user:password@localhost:5433/checksplitter`) |
| `FREE_SCANS_PER_MONTH` | Лимит бесплатных сканирований (по умолчанию 3) |
| `SCAN_PRICE_STARS` | Цена платного сканирования в Telegram Stars |

## Стек

- **aiogram 3.x** — Telegram Bot API (long polling)
- **SQLAlchemy 2.x** — ORM (async + asyncpg)
- **Alembic** — миграции базы данных
- **OpenRouter** — LLM API для OCR (любая модель с vision)
- **PostgreSQL** — хранение сессий, голосов, платежей
- **qrcode** — генерация QR-кодов для приглашений

## Тесты

```bash
# Все тесты (используют SQLite in-memory, PostgreSQL не нужен)
uv run pytest

# Конкретный тест
uv run pytest tests/test_calculator.py::test_shared_dish -v
```

## Монетизация

Freemium-модель с оплатой через Telegram Stars:
- Бесплатный лимит сканирований в месяц (настраивается)
- После лимита — оплата через Stars за каждое сканирование
- Оплаченные сканы сохраняются и расходуются при следующих OCR-запросах
