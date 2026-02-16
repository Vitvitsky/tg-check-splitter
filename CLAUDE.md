# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Telegram bot for splitting restaurant bills. Users photograph receipts, LLM (via OpenRouter) extracts items, participants join via QR/deep link, vote on dishes with quantity support, choose individual tip %, bot calculates per-person shares.

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

# Start postgres (required for bot, not for tests)
docker compose up -d
```

## Architecture

Monolith: aiogram 3.x (long polling) + SQLAlchemy 2.x (async) + PostgreSQL.

- `bot/handlers/` — aiogram routers: start (deep link join), check (photo + OCR), voting (quantity-aware inline buttons + per-person tips), admin (QR, unvoted handling, settlement), payment (Telegram Stars)
- `bot/services/` — business logic: ocr (OpenRouter LLM with vision), session (CRUD + vote cycling), calculator (quantity-aware share splitting with per-person tips), quota (freemium + paid scans)
- `bot/models/` — SQLAlchemy ORM: Session, SessionPhoto, SessionItem, SessionMember (tip_percent, confirmed), ItemVote (quantity), UserQuota (paid_scans), Payment
- `bot/keyboards/` — inline keyboard factories: check, voting (with tip/summary keyboards), admin
- `bot/config.py` — pydantic-settings, access via `get_settings()` (lazy)
- `bot/db.py` — lazy `get_engine()` / `get_async_session()`
- `bot/middlewares.py` — DB session injection into handlers via `data["db"]`

## Key Patterns

- **Lazy config/DB**: `get_settings()` and `get_async_session()` defer initialization — no .env required at import time (important for tests)
- **DB session via middleware**: `DbSessionMiddleware` injects `db: AsyncSession` into every handler
- **FSM for multi-step flows**: `CheckStates` (photo collection, OCR review, item editing), `VotingStates` (custom tip input)
- **Virtual sessions**: No real Telegram groups — users interact in DMs, linked by `invite_code` deep links
- **Admin is a SessionMember**: `create_session()` auto-adds admin as member so they can vote and receive notifications
- **Quantity-aware voting**: `cycle_vote()` increments claimed quantity (0→1→2→...→max→0), not boolean toggle
- **Per-person tips**: Each participant chooses their own tip %, stored on SessionMember, calculator applies individually
- **OCR resilience**: Strips LLM special tokens (`<|begin_of_box|>`), extracts JSON via regex, handles truncated responses
- **Tests use in-memory SQLite**: `conftest.py` provides `db_session` fixture via aiosqlite, no Postgres needed
- **All relationship loading is `selectin`**: Async-safe eager loading on all one-to-many relationships
- **UUID primary keys** on all tables, `BigInteger` for Telegram user IDs

## User Flow

1. Admin sends photo(s) → OCR extracts items → admin confirms/edits
2. QR code + invite link generated → participants join via deep link
3. Everyone (including admin) selects dishes with quantity support → chooses tip % → sees personal summary → confirms
4. Admin sees confirmation progress (2/3) → finishes voting → handles unvoted items → settles
5. All participants receive final notification with their share
