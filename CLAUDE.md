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
uv run ruff check core/ bot/ api/ tests/ && uv run ruff format core/ bot/ api/ tests/

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

A second isolation trap, same shape: application modules do `from core.config import
get_settings`, which binds the function by value, so `patch("core.config.get_settings")`
never reaches them — they kept reading the developer's own `.env`. `test_get_quota`
asserts a free allowance of 3 and began failing the moment someone set
`FREE_SCANS_PER_MONTH=5` locally, with no code change at all. An autouse fixture now
pins the environment (`tests/env.py`), which pydantic-settings prefers over `env_file`,
so every `Settings()` built during a run sees test values regardless of the call site.
Verify with `FREE_SCANS_PER_MONTH=99 uv run pytest` — it must still pass.

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

## Connections cost ~400x what queries do

Measured on this host: opening a PostgreSQL connection ~80 ms, a query on an established
one ~0.19 ms. SQLAlchemy's default `pool_size=5` therefore capped `/api/quota` at ~22–32
req/s — every burst past five had to open overflow connections, which are closed on
release rather than pooled, so the cost was paid over and over. With `pool_size=20` and a
warm pool the same endpoint does 105–130 req/s.

Two traps here. `pool_size`/`max_overflow` must **not** be passed for SQLite URLs —
StaticPool/NullPool reject them and `create_async_engine` raises `TypeError`; nothing in
the suite calls `get_engine()`, so 152 green tests did not notice (`tests/test_db_engine.py`
now covers both branches). And `get_settings()` is `lru_cache`d because `api/auth.py`
calls it on every authenticated request; uncached it re-parsed the environment, reading
`.env` from disk where present — synchronous I/O on the event loop.

Query counts are guarded by `tests/test_api/test_query_counts.py` rather than timings:
`GET /api/sessions/my` was 5n+1 queries (251 queries / 505 ms at 50 sessions) and is now
exactly 1, with the counts computed as correlated subqueries. `correlate(Session)` on
those subqueries is required — the outer query joins `SessionMember`, and auto-correlation
would otherwise strip it from the subquery's FROM and fail outright.

## Quota is the paywall — treat it as one

`POST /api/quota/reset` used to zero the caller's free-scan counter with no authorization
check and no caller in the frontend. It has been removed, not gated. Quota resets only on
the monthly boundary inside `QuotaService`.

Prices live server-side in `SCAN_PACKS` (`api/routes/quota.py`); the client names a pack
size, never an amount. The invoice is created by the API but *credited* by the bot —
Telegram delivers payment updates over the bot connection only.

A scan is charged for a *parsed receipt*, not for an attempt. `trigger_ocr` collects the
photos before charging, and every exit that yields no items — provider error, deadline,
unparseable response, zero items — calls `refund_scan()`. `use_scan()` returns which
bucket it charged (`"free"` / `"paid"`) precisely so the refund goes back where it came
from; drop that value and a paid scan quietly becomes a free one. Any new failure path in
that handler has to refund too.

## Settlement happens once, and freezes the session

`POST /settle` calls `claim_settlement()` — a conditional `UPDATE … WHERE status <>
'settled'` — *before* reading anything. Exactly one caller gets `True` and sends the push
notifications; retries recompute the same figures and return them quietly. It used to
re-notify the whole table on every call.

Shares are deliberately **not** stored. They do not need to be, because settling also
closes the session: `_require_open()` in `api/routes/voting.py` and `must_be_open` in
`api/routes/ocr.py` reject votes, tips, confirmations and receipt edits with `409
session_settled`. With the inputs frozen, recomputing on read gives the same answer
forever. Remove those guards and the idempotency goes with them — shares are computed on
read, so a later vote would silently disagree with the amount already pushed to everyone.

Reads (`/shares`, `/my-share`) stay open after settlement, and `closed_at` is finally
written (it was on the model, never set).

`unconfirm_member()` reopens a selection **without** clearing `tip_percent`. It used to
blank it, and nothing put it back, so confirm → change your mind → confirm again settled
that member at 0% — silently, with the chosen tip gone from the database. Found by an
end-to-end run, not by the suite; `TestTipSurvivesUnconfirm` covers it now.

## OCR must finish before nginx gives up

Photos go to the LLM concurrently (`OcrService.parse_receipt`, capped by
`_MAX_CONCURRENT_PHOTOS`), and the whole call sits inside
`asyncio.timeout(_OCR_DEADLINE_SECONDS)` — 240 s against nginx's 300 s
`proxy_read_timeout`. That ordering is the point: once nginx times out the connection is
gone and no handler is left to refund the scan, so the app has to fail first.

They used to run one after another at 120 s each, which put any receipt of three or more
photos past nginx's limit. `_MAX_PHOTOS` (5, enforced on upload *and* at OCR, and
mirrored in `ScanPage.tsx`) keeps the worst case inside the deadline. Raising the photo
cap or the per-photo timeout means rechecking this arithmetic and the nginx value.

## Receipt photos: on the row, and short-lived by construction

`session_photos.data` (BYTEA, nullable, **deferred**) holds the uploaded bytes. They used
to live in `app.state.photo_storage`, a process-local dict with no eviction — a restart
stranded every in-flight session, only one worker could ever run, and it grew forever.

Cleanup needs no sweeper, no TTL job and no disk budget, because a photo's useful life is
minutes — upload until OCR succeeds — and two mechanisms already cover it:

* `clear_photo_bytes()` nulls the column right after a successful OCR. This is where
  effectively all the volume goes; steady state is ~zero.
* `session_photos.session_id` cascades (migration `f1a2b3c4d5e6`), so anything that never
  reached OCR dies with its session.

Bytes are deliberately **kept** when OCR fails: that scan is refunded and retryable.

`deferred=True` is load-bearing. `Session.photos` is `lazy="selectin"`, so without it
every `GET /api/sessions/{id}` — which the Mini App polls — would drag the JPEGs along.
Read them through `SessionService.get_photo_bytes()` (an explicit `select`), never via
`photo.data`: the attribute would emit a lazy load per photo and raise `MissingGreenlet`
in async context.

Sizing, for reference: the client resizes to 2048 px JPEG (~0.3–1 MB), the server caps a
photo at 5 MB and a receipt at `_MAX_PHOTOS` (5), so a session is ≤25 MB at its very worst
and 1–3 MB in practice.

The remaining obstacle to running more than one API worker is `ConnectionManager` in
`api/ws.py` — broadcasts only reach clients attached to the same process.

## Every route needs a way in

Twelve routes, and `/quota` had no inbound navigation at all — `useQuota` and
`usePurchaseScans` were called only from inside the page nothing linked to. The Stars
purchase worked end to end and could not be reached, while ScanPage's out-of-quota
message pointed at it. Monetisation was unreachable from the UI.

It now has two entrances (the quota card on HomePage, the button on a 402 in ScanPage),
and `/session/:code/share` has one during voting instead of only after settlement.
`/session/:code` is deliberately entered from outside only — `?startapp=` and bot links.

Worth re-running after adding a page or a link:

```bash
cd webapp/src
grep -oE 'path="[^"]+"' App.tsx                       # declared
grep -rhoE 'navigate\(`[^`]+`|navigate\("[^"]+"' pages components   # reachable
```

Pages resolve `:code` (an invite code) to `session.id` via `useSession(code)` before
calling any hook that takes a session id — `useShares`, `useVote`, `useWebSocket` and
friends all want the UUID. Passing the code straight through is the easy mistake here;
every page currently does it correctly.

## SPA routing depends on the API's fallback

The frontend uses `BrowserRouter`, so `/session/<code>/vote` is a real URL a user can
reload into. `StaticFiles(html=True)` mounted at `/` 404s on unknown paths, so `api/app.py`
serves `index.html` from a catch-all `GET /{spa_path:path}` instead, with `/assets`
mounted separately and `/api/...` explicitly kept as a 404. Bot buttons and push
notifications rely on this and link to real routes.

## The Telegram SDK throws mid-handler unless it is initialised

`main.tsx` must call **both** `init()` and `restoreInitData()`. They are separate steps:
`init()` only configures the environment and attaches event receivers, so `initDataUser`
stays empty until `restoreInitData()` runs.

Skipping them does not fail loudly. Every `@telegram-apps/sdk` v2 function is wrapped in a
guard that **throws** when the version signal is unset (`ERR_NOT_INITIALIZED`) or when the
client does not support the method (`ERR_NOT_SUPPORTED` — haptics on Desktop). The throw
is synchronous inside the click handler and kills everything after it:

```js
haptic.impactOccurred("light");     // throws
navigate(`/session/${code}/tip`);   // never runs — "the button does nothing"
```

Three separate bug reports on 2026-08-04 came from this one omission: Confirm Selection
did nothing, `+/-` moved but no `POST /vote` ever left the device (optimistic state
updates *before* the throw, `mutate` is called *after* it), and a member could not claim
the second of two portions.

Two rules follow. **Never put an SDK call before the action it decorates** — haptics are
wrapped in `useHaptic()` so they can only no-op. And **never let a missing Telegram
identity fall back to a plausible number**: `user?.id ?? 0` turned a broken SDK into wrong
billing arithmetic instead of an error, because `votes.filter(v => v.user_tg_id !== 0)`
excluded nobody and counted the user's own claim as someone else's. Where a per-user cap
is computed, prefer "everything minus mine" over filtering by id, and let the server —
which knows the real caller — hold the real bound.

## react-query: the mutation object is a new reference every render

`useMutation` returns `{ ...result, mutate, mutateAsync }` — a fresh object literal on each
render. `mutate` itself is `useCallback`-wrapped and stable.

So a mutation object in a `useEffect` dependency array is a self-feeding loop. The debounced
tip autosave in `TipPage` did exactly this: effect re-ran every render → timer reset → once
300 ms passed, `POST /tip` → `isPending` changed → render → `onSuccess` invalidated
`my-share`/`shares` → refetch → render. 142 requests and a button flickering
"Confirm & Pay" ↔ "Saving...". Depend on `mutate`, never on the mutation.

Harmless in `useCallback` (a recreated callback does not invoke itself), which is why the
other pages get away with it.

## Debugging the Mini App without a console

There is no devtools on the phone, so the server is the instrument. What actually resolved
every bug above:

```bash
docker logs tg-check-splitter-api-1 2>&1 | grep -E 'POST /api/sessions/[^ ]+/(vote|tip|confirm)'
docker exec tg-check-splitter-db-1 psql -U user -d checksplitter -c "select * from item_votes;"
```

The bot and the API are separate services now, so `docker compose logs bot` and
`docker compose logs api` are separate too — a Mini App bug never has to be read out of
polling noise.

Two tricks worth knowing. **A lazy chunk request proves navigation happened** — the routes
are `lazy()`, so if `GET /assets/TipPage-*.js` never appears, the client never reached
`/tip`, no matter what the user describes. And **the API can be probed directly** by signing
initData with `BOT_TOKEN` (HMAC-SHA256 over the sorted data-check-string, `Authorization:
tma <initData>`), which separates a broken client from a broken endpoint.

Note the DB table is `session_items`, not `items`, and credentials come from
`DATABASE_URL` in `.env` (`user` / `checksplitter`).

## Split-equal is integer-only

`split_remaining_equally()` distributes whole units and gives the indivisible remainder to
the least-claimed members, so the total billed always equals the receipt. It cannot split
one dish across three people evenly — `ItemVote.quantity` is an `Integer`. The old code
faked fairness with `max(1, remaining // n)` and handed out four units for one unclaimed
unit, overbilling the table. If fractional shares are ever wanted, that is a schema change.

## Backlog lives in docs/BACKLOG.md

What is deliberately not built, each with the trigger that would justify building it —
multi-worker + Redis pub/sub, a `user_activity` table for stable DAU/MAU, rewriting the
backend in Rust, and the resource arithmetic behind them
(measured, not estimated). Read it before adding infrastructure or changing the stack; the
answers to "should we add Redis" and "should this be Rust" are in there with numbers.

Analytics today come from `tools/stats.sh`, which unions the four tables that already
carry a `user_tg_id` and a timestamp. One caveat worth knowing before quoting a figure:
`DELETE /api/sessions/history` cascades away members and votes, so historical DAU is not
reproducible — yesterday's number can shrink. That is the argument for backlog item B,
not a bug in the script.

## Deployment notes

Three services from one image: `migrate` (one-shot, `alembic upgrade head`), `api` and
`bot`. Both depend on `migrate` completing and on nothing else — killing one does not
touch the other. There is no `entrypoint.sh` any more; each service carries its own
`command`. The `api` healthcheck is observational only: Docker does not restart an
unhealthy container, and nothing declares `depends_on: api: service_healthy`, so a hung
but alive uvicorn stays hung — the probe tells `docker compose ps` about it, it does not
act on it.

`restart: unless-stopped` will not bring a service back after `docker compose kill` or
`docker compose stop`: the daemon marks those containers manually stopped and skips the
restart policy. A real crash *is* restarted. So verifying the policy means killing the
process inside the container, not the container itself — the acceptance run for the split
used `docker compose exec bot python -c "os.kill(<bot pid>, SIGKILL)"`, and only then did
`RestartCount` go to 1. After a deliberate `kill`/`stop`, put the service back with
`docker compose up -d`.

**The frontend is baked into the image**, so a `webapp/` change is not live until
`docker compose up -d --build api`. That form is right for `webapp/` only — it rebuilds
the shared image but recreates just `api` (and `migrate`), leaving `bot` on the old one,
so a change in `core/` or `bot/` needs `docker compose up -d --build` with no service
named. Rebuilding is not enough on its own either: Telegram
caches the Mini App hard, and the phone must clear its cache before it sees the new bundle.
Both steps look identical to "the fix did not work" — verify instead by asking the server
which bundle it serves, since Vite hashes every chunk:

```bash
curl -s http://127.0.0.1:8005/ | grep -oE '/assets/index-[A-Za-z0-9_-]+\.js'
```

`nginx/tg-check-splitter.conf` declares its own `map $http_upgrade $connection_upgrade`.
The sibling `portfolio.conf` already declares an identical one and all `sites-*` share a
single http context, so this vhost worked without it — ours exists so the file does not
depend on a variable surviving in a file that `certbot --nginx` rewrites in place.
Duplicate identical maps are accepted (verified with `nginx -t` on 1.28), so the two do
not clash. Do not "fix" this by deleting one without checking the other is still there.
