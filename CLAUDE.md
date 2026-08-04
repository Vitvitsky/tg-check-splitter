# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Structure, the REST/WebSocket route tables and the DB model reference live in `README.md`.
This file covers what the code does not say out loud.

## Project

Telegram Mini App (+ thin bot) for splitting restaurant bills. Users photograph receipts,
an LLM (Z.AI `glm-4.6v`) extracts items, participants join via QR/deep link, vote on dishes
with quantity support, choose an individual tip %, the app calculates per-person shares.

## Commands

```bash
# Run bot locally (requires .env with BOT_TOKEN, ZAI_API_KEY, DATABASE_URL)
uv run python -m bot

# Run API server (serves the REST API, WebSocket and the built Mini App)
uv run python -m api

# Tests / lint
uv run pytest
uv run pytest tests/test_calculator.py::test_shared_dish -v
uv run ruff check bot/ api/ tests/ && uv run ruff format bot/ api/ tests/

# Migrations
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head

# Frontend
cd webapp && npm ci && npm run build   # -> webapp/dist/, served by the API

# Postgres (needed by the bot/API, not by the tests)
docker compose up -d db
```

## The Mini App owns the product; the bot does not

`bot/handlers/` is deliberately two files. `start.py` greets and hands invites to the
Mini App, `payment.py` settles Stars purchases — that is all. Scanning, editing, voting,
tips and settlement live in `api/` + `webapp/`.

There used to be a second, complete implementation of that flow in
`bot/handlers/{check,voting,admin}.py` on aiogram FSM and inline keyboards, against the
same tables. Do not reintroduce it — a feature added to one copy silently does not exist
in the other, and the seam between them leaked: the QR pointed at `t.me/<bot>?start=`,
so the bot joined the user and then sent a `?startapp=` button that no frontend code
ever read, dropping participants on the home screen instead of their check.

## Test suite gotcha: SQLite hides integrity bugs

SQLite ignores foreign keys unless `PRAGMA foreign_keys=ON` is set per connection. That
is not a style detail: missing `ON DELETE` rules reached production with 109 green tests,
and `DELETE /api/sessions/history` failed **every** time (the admin is always a member of
their own session, so there was always a child row to orphan).

All test engines therefore come from `make_test_engine()` in `tests/db.py`. Never call
`create_async_engine` directly in a test — that silently opts back out of enforcement.

Migrations are PostgreSQL-only and SQLite never sees them: `f1a2b3c4d5e6` uses `ctid` and
`DELETE … USING`. Verify DDL changes against a real database (recipe in README → Тесты).

`MIN(id)` is not available for dedupe — `id` is a `uuid` and PostgreSQL has no ordering
aggregate for that type. Rank duplicates by their timestamp with `ctid` as tie-break.

## Claims are serialised per dish — keep them that way

Every claim path reads the total already claimed and then writes. That read-then-write
window is the whole product: everyone at the table taps at once. Under READ COMMITTED
two people tapping the last portion both read "free" and both insert, and the table
gets billed twice for one dish. The unique constraint does not catch it — it is per
(item, user), and these are different users.

So `cycle_vote`, `set_vote`, `add_vote_all` and `split_remaining_equally` all open with
`_lock_item()` (`SELECT … FOR UPDATE` on the dish row). Any new path that mutates
`ItemVote` must do the same, and must not commit mid-distribution — a commit drops the
lock and reopens the window. That is why `split_remaining_equally` stages every member's
units via `_stage_vote_units()` and commits once at the end.

`tests/test_concurrency.py` proves it, and needs a real PostgreSQL: SQLite serialises
writers and its dialect does not emit FOR UPDATE, so it cannot show the bug *or* the
fix. Those tests skip silently without `TEST_DATABASE_URL` — check they actually ran
before trusting a change here.

## Quota is the paywall — treat it as one

`POST /api/quota/reset` used to zero the caller's free-scan counter with no authorization
check and no caller in the frontend. It has been removed, not gated. Quota resets only on
the monthly boundary inside `QuotaService`.

Prices live server-side in `SCAN_PACKS` (`api/routes/quota.py`); the client names a pack
size, never an amount. The invoice is created by the API but *credited* by the bot —
Telegram delivers payment updates over the bot connection only.

Two known holes still open here: a scan is consumed **before** the OCR call, so a failed
OCR burns it with no refund; and `settle` is not idempotent, so calling it twice re-sends
push notifications to everyone.

## Photos live in process memory

`app.state.photo_storage` is a plain dict with no TTL and no size cap — uploaded receipt
bytes stay until the process dies. Consequences: the API must run as a single worker, and
a restart leaves `session_photos` rows whose bytes are gone, which surfaces as
"No photos available for OCR" with no way out for that session.

## SPA routing depends on the API's fallback

The frontend uses `BrowserRouter`, so `/session/<code>/vote` is a real URL a user can
reload into. `StaticFiles(html=True)` mounted at `/` 404s on unknown paths, so `api/app.py`
serves `index.html` from a catch-all `GET /{spa_path:path}` instead, with `/assets`
mounted separately and `/api/...` explicitly kept as a 404. Bot buttons and push
notifications rely on this and link to real routes.

## Split-equal is integer-only

`split_remaining_equally()` distributes whole units and gives the indivisible remainder to
the least-claimed members, so the total billed always equals the receipt. It cannot split
one dish across three people evenly — `ItemVote.quantity` is an `Integer`. The old code
faked fairness with `max(1, remaining // n)` and handed out four units for one unclaimed
unit, overbilling the table. If fractional shares are ever wanted, that is a schema change.

## Deployment notes

`entrypoint.sh` runs migrations, then the bot and uvicorn in the same container with
`wait -n`. `nginx/tg-check-splitter.conf` defines its own `map $http_upgrade
$connection_upgrade` — nothing else on the host does, and without it `nginx -t` fails
outright. If another vhost ever defines the same map, drop ours (a duplicate map is an
error).
