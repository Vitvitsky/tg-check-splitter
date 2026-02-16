# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Telegram bot for splitting restaurant bills. Users photograph receipts, LLM (via OpenRouter) extracts items, participants vote on their dishes via inline keyboards, bot calculates shares with tips.

## Commands

```bash
# Run bot locally (requires .env with BOT_TOKEN, OPENROUTER_API_KEY, DATABASE_URL)
uv run python -m bot

# Run all tests
uv run pytest

# Run single test file or test
uv run pytest tests/test_calculator.py -v
uv run pytest tests/test_calculator.py::test_shared_dish -v

# Lint and format
uv run ruff check bot/ tests/
uv run ruff format bot/ tests/

# Database migrations
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head

# Docker
docker compose up --build
```

## Architecture

Monolith: aiogram 3.x (long polling) + SQLAlchemy 2.x (async) + PostgreSQL.

- `bot/handlers/` — aiogram routers: start (deep link join), check (photo + OCR), voting (inline buttons), admin (QR, tips, settlement), payment (Telegram Stars)
- `bot/services/` — business logic: ocr (OpenRouter LLM), session (CRUD), calculator (share splitting), quota (freemium limits)
- `bot/models/` — SQLAlchemy ORM: Session, SessionPhoto, SessionItem, SessionMember, ItemVote, UserQuota, Payment
- `bot/keyboards/` — inline keyboard factories
- `bot/config.py` — pydantic-settings, access via `get_settings()` (lazy, no module-level instance)
- `bot/db.py` — lazy `get_engine()` / `get_async_session()` (deferred to avoid crash without .env)
- `bot/middlewares.py` — DB session injection into handlers via `data["db"]`

## Key Patterns

- **Lazy config/DB**: `get_settings()` and `get_async_session()` defer initialization — no .env required at import time (important for tests)
- **DB session via middleware**: `DbSessionMiddleware` injects `db: AsyncSession` into every handler
- **FSM for multi-step flows**: `CheckStates` (photo collection, OCR review, item editing), `AdminStates` (custom tip input)
- **Virtual sessions**: No real Telegram groups — users interact in DMs, linked by `invite_code` deep links (`t.me/bot?start=<code>`)
- **Tests use in-memory SQLite**: `conftest.py` provides `db_session` fixture via aiosqlite, no Postgres needed
- **OpenRouter API**: OpenAI-compatible endpoint, model configurable via `OPENROUTER_MODEL` env var
- **All relationship loading is `selectin`**: Async-safe eager loading on all one-to-many relationships
- **UUID primary keys** on all tables, `BigInteger` for Telegram user IDs
