# Check Splitter Bot — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Telegram bot that splits restaurant bills via photo OCR, virtual sessions, and inline voting.

**Architecture:** Monolith Python app (aiogram 3.x + SQLAlchemy 2.x async) with long polling. Virtual sessions instead of real Telegram groups. OCR via OpenRouter LLM API. Payments via Telegram Stars.

**Tech Stack:** Python 3.12, aiogram 3.x, SQLAlchemy 2.x (async), Alembic, PostgreSQL, OpenRouter API, Docker Compose, qrcode library.

**Design doc:** `docs/plans/2026-02-16-check-splitter-design.md`

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `bot/__init__.py`
- Create: `bot/config.py`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.gitignore`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create `pyproject.toml`**

```toml
[project]
name = "tg-check-splitter"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "aiogram>=3.15,<4",
    "sqlalchemy[asyncio]>=2.0,<3",
    "asyncpg>=0.30,<1",
    "alembic>=1.14,<2",
    "httpx>=0.28,<1",
    "pydantic>=2.0,<3",
    "pydantic-settings>=2.0,<3",
    "qrcode[pil]>=8.0,<9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9",
    "pytest-asyncio>=0.24,<1",
    "pytest-cov>=6.0,<7",
    "aiosqlite>=0.20,<1",
    "ruff>=0.8,<1",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 99
```

**Step 2: Create `.env.example`**

```env
BOT_TOKEN=your-telegram-bot-token
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=anthropic/claude-sonnet-4-5-20250929
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/checksplitter
FREE_SCANS_PER_MONTH=3
SCAN_PRICE_STARS=1
```

**Step 3: Create `bot/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str
    openrouter_api_key: str
    openrouter_model: str = "anthropic/claude-sonnet-4-5-20250929"
    database_url: str
    free_scans_per_month: int = 3
    scan_price_stars: int = 1

    model_config = {"env_file": ".env"}


settings = Settings()
```

**Step 4: Create `bot/__init__.py`** (empty)

**Step 5: Create `.gitignore`**

```
__pycache__/
*.pyc
.env
*.egg-info/
.venv/
.pytest_cache/
.ruff_cache/
```

**Step 6: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY . .
CMD ["python", "-m", "bot"]
```

**Step 7: Create `docker-compose.yml`**

```yaml
services:
  bot:
    build: .
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: checksplitter
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

**Step 8: Create `tests/__init__.py`** (empty) and `tests/conftest.py`**

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.models.base import Base


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()
```

**Step 9: Install dependencies and verify**

Run: `pip install -e ".[dev]"`
Expected: installs without errors

**Step 10: Commit**

```bash
git add -A
git commit -m "chore: project scaffolding — pyproject, docker, config, test setup"
```

---

## Task 2: Database Models + Alembic

**Files:**
- Create: `bot/models/__init__.py`
- Create: `bot/models/base.py`
- Create: `bot/models/session.py`
- Create: `bot/models/user_quota.py`
- Create: `bot/models/payment.py`
- Create: `bot/db.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing test**

```python
# tests/test_models.py
import uuid
from decimal import Decimal

from bot.models.session import ItemVote, Session, SessionItem, SessionMember, SessionPhoto


async def test_create_session(db_session):
    session = Session(admin_tg_id=123456, invite_code="abc123")
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    assert session.id is not None
    assert session.status == "created"
    assert session.tip_percent == 0


async def test_session_with_items_and_votes(db_session):
    session = Session(admin_tg_id=111, invite_code="test1")
    db_session.add(session)
    await db_session.flush()

    item = SessionItem(session_id=session.id, name="Pizza", price=Decimal("650.00"), quantity=1)
    db_session.add(item)
    await db_session.flush()

    vote = ItemVote(item_id=item.id, user_tg_id=222)
    db_session.add(vote)
    await db_session.commit()

    await db_session.refresh(item, attribute_names=["votes"])
    assert len(item.votes) == 1
    assert item.votes[0].user_tg_id == 222


async def test_session_photos(db_session):
    session = Session(admin_tg_id=111, invite_code="test2")
    db_session.add(session)
    await db_session.flush()

    photo = SessionPhoto(session_id=session.id, tg_file_id="AgACAgIAA...")
    db_session.add(photo)
    await db_session.commit()

    await db_session.refresh(session, attribute_names=["photos"])
    assert len(session.photos) == 1


async def test_session_members(db_session):
    session = Session(admin_tg_id=111, invite_code="test3")
    db_session.add(session)
    await db_session.flush()

    member = SessionMember(session_id=session.id, user_tg_id=222, display_name="Alice")
    db_session.add(member)
    await db_session.commit()

    await db_session.refresh(session, attribute_names=["members"])
    assert len(session.members) == 1
    assert session.members[0].display_name == "Alice"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL (imports don't exist)

**Step 3: Create `bot/models/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

**Step 4: Create `bot/models/session.py`**

```python
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    admin_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="created", nullable=False)
    tip_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    photos: Mapped[list["SessionPhoto"]] = relationship(back_populates="session", lazy="selectin")
    items: Mapped[list["SessionItem"]] = relationship(back_populates="session", lazy="selectin")
    members: Mapped[list["SessionMember"]] = relationship(back_populates="session", lazy="selectin")


class SessionPhoto(Base):
    __tablename__ = "session_photos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    tg_file_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped["Session"] = relationship(back_populates="photos")


class SessionItem(Base):
    __tablename__ = "session_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    session: Mapped["Session"] = relationship(back_populates="items")
    votes: Mapped[list["ItemVote"]] = relationship(back_populates="item", lazy="selectin")


class SessionMember(Base):
    __tablename__ = "session_members"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    user_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped["Session"] = relationship(back_populates="members")


class ItemVote(Base):
    __tablename__ = "item_votes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("session_items.id"), nullable=False)
    user_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    item: Mapped["SessionItem"] = relationship(back_populates="votes")
```

**Step 5: Create `bot/models/user_quota.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.base import Base


class UserQuota(Base):
    __tablename__ = "user_quotas"

    user_tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    free_scans_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quota_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

**Step 6: Create `bot/models/payment.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    stars_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    telegram_charge_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
```

**Step 7: Create `bot/models/__init__.py`**

```python
from bot.models.base import Base
from bot.models.payment import Payment
from bot.models.session import ItemVote, Session, SessionItem, SessionMember, SessionPhoto
from bot.models.user_quota import UserQuota

__all__ = [
    "Base",
    "ItemVote",
    "Payment",
    "Session",
    "SessionItem",
    "SessionMember",
    "SessionPhoto",
    "UserQuota",
]
```

**Step 8: Create `bot/db.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import settings

engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

**Step 9: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: all 4 tests PASS

**Step 10: Set up Alembic**

Run: `alembic init alembic`

Then edit `alembic/env.py` to use async engine and import models:

```python
# alembic/env.py — key changes:
# 1. Set target_metadata = Base.metadata
# 2. Use async engine from bot.db
# See alembic async template for full file
```

Edit `alembic.ini`: set `sqlalchemy.url` to use env variable (override in env.py).

Run: `alembic revision --autogenerate -m "initial tables"`
Run: `alembic upgrade head` (against local postgres or skip if no DB yet)

**Step 11: Commit**

```bash
git add -A
git commit -m "feat: database models — Session, Items, Votes, Quota, Payment + Alembic"
```

---

## Task 3: Calculator Service

**Files:**
- Create: `bot/services/calculator.py`
- Test: `tests/test_calculator.py`

**Step 1: Write the failing tests**

```python
# tests/test_calculator.py
from decimal import Decimal

from bot.services.calculator import calculate_shares


def test_simple_split():
    """Each person took one unique dish."""
    items = [
        {"price": Decimal("650"), "votes": [111]},
        {"price": Decimal("450"), "votes": [222]},
    ]
    result = calculate_shares(items, tip_percent=0)
    assert result == {111: Decimal("650"), 222: Decimal("450")}


def test_shared_dish():
    """Two people share one dish."""
    items = [
        {"price": Decimal("650"), "votes": [111, 222]},
    ]
    result = calculate_shares(items, tip_percent=0)
    assert result == {111: Decimal("325"), 222: Decimal("325")}


def test_with_tips():
    """10% tips applied."""
    items = [
        {"price": Decimal("1000"), "votes": [111]},
    ]
    result = calculate_shares(items, tip_percent=10)
    assert result == {111: Decimal("1100")}


def test_rounding_up():
    """Shares round up to whole unit."""
    items = [
        {"price": Decimal("100"), "votes": [111, 222, 333]},
    ]
    result = calculate_shares(items, tip_percent=0)
    # 100 / 3 = 33.33... → ceil to 34 each
    assert result[111] == Decimal("34")
    assert result[222] == Decimal("34")
    assert result[333] == Decimal("34")


def test_multiple_items_per_person():
    """One person votes for multiple items."""
    items = [
        {"price": Decimal("650"), "votes": [111, 222]},
        {"price": Decimal("450"), "votes": [222]},
    ]
    result = calculate_shares(items, tip_percent=10)
    # 111: 325 * 1.1 = 357.5 → 358
    # 222: (325 + 450) * 1.1 = 852.5 → 853
    assert result == {111: Decimal("358"), 222: Decimal("853")}


def test_no_votes_item_ignored():
    """Items with no votes don't affect calculation."""
    items = [
        {"price": Decimal("500"), "votes": [111]},
        {"price": Decimal("300"), "votes": []},
    ]
    result = calculate_shares(items, tip_percent=0)
    assert result == {111: Decimal("500")}


def test_empty_items():
    """No items returns empty dict."""
    result = calculate_shares([], tip_percent=0)
    assert result == {}
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_calculator.py -v`
Expected: FAIL (import error)

**Step 3: Implement calculator**

```python
# bot/services/calculator.py
import math
from decimal import Decimal


def calculate_shares(
    items: list[dict],
    tip_percent: int,
) -> dict[int, Decimal]:
    """Calculate each user's share from voted items.

    Args:
        items: [{"price": Decimal, "votes": [user_tg_id, ...]}]
        tip_percent: tip percentage (0-100)

    Returns:
        {user_tg_id: total_amount} with amounts rounded up to whole units.
    """
    raw_shares: dict[int, Decimal] = {}

    for item in items:
        voters = item["votes"]
        if not voters:
            continue
        per_person = item["price"] / len(voters)
        for user_id in voters:
            raw_shares[user_id] = raw_shares.get(user_id, Decimal("0")) + per_person

    tip_multiplier = Decimal(1) + Decimal(tip_percent) / Decimal(100)

    return {
        user_id: Decimal(math.ceil(share * tip_multiplier))
        for user_id, share in raw_shares.items()
    }
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_calculator.py -v`
Expected: all 7 tests PASS

**Step 5: Commit**

```bash
git add bot/services/calculator.py tests/test_calculator.py
git commit -m "feat: calculator service — split shares with tips and rounding"
```

---

## Task 4: OCR Service (OpenRouter)

**Files:**
- Create: `bot/services/ocr.py`
- Test: `tests/test_ocr.py`

**Step 1: Write the failing tests**

```python
# tests/test_ocr.py
import json
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from bot.services.ocr import OcrResult, OcrService


@pytest.fixture
def ocr_service():
    return OcrService(api_key="test-key", model="test/model")


MOCK_LLM_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": json.dumps({
                    "items": [
                        {"name": "Пицца Маргарита", "price": 650, "quantity": 1},
                        {"name": "Том Ям", "price": 450, "quantity": 2},
                    ],
                    "total": 1550,
                    "currency": "RUB",
                })
            }
        }
    ]
}


async def test_parse_receipt_single_photo(ocr_service):
    mock_response = AsyncMock()
    mock_response.json.return_value = MOCK_LLM_RESPONSE
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        result = await ocr_service.parse_receipt([b"fake-image-bytes"])

    assert isinstance(result, OcrResult)
    assert len(result.items) == 2
    assert result.items[0].name == "Пицца Маргарита"
    assert result.items[0].price == Decimal("650")
    assert result.total == Decimal("1550")


async def test_parse_receipt_multiple_photos(ocr_service):
    mock_response = AsyncMock()
    mock_response.json.return_value = MOCK_LLM_RESPONSE
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await ocr_service.parse_receipt([b"photo1", b"photo2"])

    # Verify multiple images sent in one request
    call_args = mock_post.call_args
    content = call_args[1]["json"]["messages"][0]["content"]
    image_parts = [p for p in content if p.get("type") == "image_url"]
    assert len(image_parts) == 2


async def test_validation_warning_on_mismatch(ocr_service):
    bad_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "items": [{"name": "Item", "price": 100, "quantity": 1}],
                        "total": 200,
                        "currency": "RUB",
                    })
                }
            }
        ]
    }
    mock_response = AsyncMock()
    mock_response.json.return_value = bad_response
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        result = await ocr_service.parse_receipt([b"photo"])

    assert result.total_mismatch is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ocr.py -v`
Expected: FAIL (import error)

**Step 3: Implement OCR service**

```python
# bot/services/ocr.py
import base64
import json
from dataclasses import dataclass, field
from decimal import Decimal

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """\
You are a receipt parser. Extract all line items from the receipt photo(s).
If multiple photos are provided, they are parts of the same receipt — merge items and remove duplicates.

Return ONLY valid JSON (no markdown, no explanation):
{
  "items": [{"name": "Item name", "price": 123.45, "quantity": 1}],
  "total": 1234.56,
  "currency": "RUB"
}

Rules:
- price is the total price for that line (price × quantity already multiplied)
- quantity is how many of that item
- total is the receipt grand total
- If you can't read a value, make your best guess and note it in the name with (?)
"""


@dataclass
class OcrItem:
    name: str
    price: Decimal
    quantity: int


@dataclass
class OcrResult:
    items: list[OcrItem]
    total: Decimal
    currency: str
    total_mismatch: bool = False


class OcrService:
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    async def parse_receipt(self, photos: list[bytes]) -> OcrResult:
        content: list[dict] = [{"type": "text", "text": "Parse this receipt:"}]
        for photo in photos:
            b64 = base64.b64encode(photo).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": content},
                    ],
                },
            )
            response.raise_for_status()

        raw = response.json()["choices"][0]["message"]["content"]
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(raw)

        items = [
            OcrItem(
                name=i["name"],
                price=Decimal(str(i["price"])),
                quantity=i.get("quantity", 1),
            )
            for i in data["items"]
        ]

        total = Decimal(str(data["total"]))
        items_sum = sum(i.price for i in items)
        mismatch = abs(items_sum - total) > total * Decimal("0.05") if total else False

        return OcrResult(
            items=items,
            total=total,
            currency=data.get("currency", "RUB"),
            total_mismatch=mismatch,
        )
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ocr.py -v`
Expected: all 3 tests PASS

**Step 5: Commit**

```bash
git add bot/services/ocr.py tests/test_ocr.py
git commit -m "feat: OCR service — OpenRouter LLM integration with multi-photo support"
```

---

## Task 5: Session Service

**Files:**
- Create: `bot/services/session.py`
- Test: `tests/test_session_service.py`

**Step 1: Write the failing tests**

```python
# tests/test_session_service.py
from bot.models.session import Session, SessionItem, SessionMember, SessionPhoto
from bot.services.session import SessionService


@pytest.fixture
def svc(db_session):
    return SessionService(db_session)


async def test_create_session(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    assert session.admin_tg_id == 111
    assert session.status == "created"
    assert len(session.invite_code) == 8


async def test_join_session(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    member = await svc.join_session(session.invite_code, user_tg_id=222, display_name="Bob")
    assert member.user_tg_id == 222
    assert member.session_id == session.id


async def test_join_session_invalid_code(svc):
    result = await svc.join_session("nonexistent", user_tg_id=222, display_name="Bob")
    assert result is None


async def test_join_session_duplicate(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    await svc.join_session(session.invite_code, user_tg_id=222, display_name="Bob")
    dup = await svc.join_session(session.invite_code, user_tg_id=222, display_name="Bob")
    assert dup is None  # already joined


async def test_add_photo(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    photo = await svc.add_photo(session.id, tg_file_id="AgACAgIAA...")
    assert photo.tg_file_id == "AgACAgIAA..."


async def test_save_ocr_items(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    items_data = [
        {"name": "Pizza", "price": 650, "quantity": 1},
        {"name": "Soup", "price": 450, "quantity": 2},
    ]
    items = await svc.save_ocr_items(session.id, items_data)
    assert len(items) == 2


async def test_toggle_vote(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    items = await svc.save_ocr_items(session.id, [{"name": "Pizza", "price": 650, "quantity": 1}])
    item_id = items[0].id

    # Vote on
    voted = await svc.toggle_vote(item_id, user_tg_id=222)
    assert voted is True

    # Vote off
    voted = await svc.toggle_vote(item_id, user_tg_id=222)
    assert voted is False


async def test_get_unvoted_items(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    items = await svc.save_ocr_items(session.id, [
        {"name": "Pizza", "price": 650, "quantity": 1},
        {"name": "Soup", "price": 450, "quantity": 1},
    ])
    await svc.toggle_vote(items[0].id, user_tg_id=222)

    unvoted = await svc.get_unvoted_items(session.id)
    assert len(unvoted) == 1
    assert unvoted[0].name == "Soup"
```

Note: add `import pytest` at top of file.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_service.py -v`
Expected: FAIL (import error)

**Step 3: Implement session service**

```python
# bot/services/session.py
import secrets
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.session import ItemVote, Session, SessionItem, SessionMember, SessionPhoto


class SessionService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create_session(self, admin_tg_id: int) -> Session:
        session = Session(
            admin_tg_id=admin_tg_id,
            invite_code=secrets.token_urlsafe(6)[:8],
        )
        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def get_session_by_invite(self, invite_code: str) -> Session | None:
        result = await self._db.execute(
            select(Session).where(Session.invite_code == invite_code)
        )
        return result.scalar_one_or_none()

    async def join_session(
        self, invite_code: str, user_tg_id: int, display_name: str
    ) -> SessionMember | None:
        session = await self.get_session_by_invite(invite_code)
        if session is None:
            return None

        existing = await self._db.execute(
            select(SessionMember).where(
                SessionMember.session_id == session.id,
                SessionMember.user_tg_id == user_tg_id,
            )
        )
        if existing.scalar_one_or_none():
            return None

        member = SessionMember(
            session_id=session.id, user_tg_id=user_tg_id, display_name=display_name
        )
        self._db.add(member)
        await self._db.commit()
        await self._db.refresh(member)
        return member

    async def add_photo(self, session_id: UUID, tg_file_id: str) -> SessionPhoto:
        photo = SessionPhoto(session_id=session_id, tg_file_id=tg_file_id)
        self._db.add(photo)
        await self._db.commit()
        await self._db.refresh(photo)
        return photo

    async def save_ocr_items(
        self, session_id: UUID, items_data: list[dict]
    ) -> list[SessionItem]:
        items = []
        for data in items_data:
            item = SessionItem(
                session_id=session_id,
                name=data["name"],
                price=Decimal(str(data["price"])),
                quantity=data.get("quantity", 1),
            )
            self._db.add(item)
            items.append(item)
        await self._db.commit()
        for item in items:
            await self._db.refresh(item)
        return items

    async def toggle_vote(self, item_id: UUID, user_tg_id: int) -> bool:
        """Returns True if vote added, False if removed."""
        existing = await self._db.execute(
            select(ItemVote).where(
                ItemVote.item_id == item_id, ItemVote.user_tg_id == user_tg_id
            )
        )
        vote = existing.scalar_one_or_none()
        if vote:
            await self._db.delete(vote)
            await self._db.commit()
            return False
        new_vote = ItemVote(item_id=item_id, user_tg_id=user_tg_id)
        self._db.add(new_vote)
        await self._db.commit()
        return True

    async def get_unvoted_items(self, session_id: UUID) -> list[SessionItem]:
        result = await self._db.execute(
            select(SessionItem)
            .where(SessionItem.session_id == session_id)
            .outerjoin(ItemVote)
            .where(ItemVote.id.is_(None))
        )
        return list(result.scalars().all())

    async def update_status(self, session_id: UUID, status: str) -> None:
        session = await self._db.get(Session, session_id)
        if session:
            session.status = status
            await self._db.commit()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_session_service.py -v`
Expected: all 8 tests PASS

**Step 5: Commit**

```bash
git add bot/services/session.py tests/test_session_service.py
git commit -m "feat: session service — create, join, photos, items, voting"
```

---

## Task 6: Inline Keyboards

**Files:**
- Create: `bot/keyboards/__init__.py`
- Create: `bot/keyboards/check.py`
- Create: `bot/keyboards/voting.py`
- Create: `bot/keyboards/admin.py`

**Step 1: Create keyboard factories**

```python
# bot/keyboards/check.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def photo_collected_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Распознать", callback_data="ocr_start")],
    ])


def ocr_result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Всё верно", callback_data="ocr_confirm"),
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="ocr_edit"),
        ],
        [InlineKeyboardButton(text="🔄 Переотправить", callback_data="ocr_retry")],
    ])
```

```python
# bot/keyboards/voting.py
from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def items_page_kb(
    items: list[dict],
    user_votes: set[UUID],
    page: int = 0,
    page_size: int = 8,
) -> InlineKeyboardMarkup:
    start = page * page_size
    end = start + page_size
    page_items = items[start:end]

    buttons = []
    for item in page_items:
        voted = "☑️" if item["id"] in user_votes else "◻️"
        voter_count = item["voter_count"]
        label = f"{voted} {item['name']} — {item['price']}₽"
        if voter_count > 0:
            label += f" ({voter_count})"
        buttons.append(
            [InlineKeyboardButton(text=label, callback_data=f"vote:{item['id']}")]
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="← Назад", callback_data=f"page:{page - 1}"))
    if end < len(items):
        nav.append(InlineKeyboardButton(text="Далее →", callback_data=f"page:{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append(
        [InlineKeyboardButton(text="✅ Готово", callback_data="vote_done")]
    )
    buttons.append(
        [InlineKeyboardButton(text="⚠️ Не вижу своё блюдо", callback_data="missing_item")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

```python
# bot/keyboards/admin.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def voting_progress_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Текущий расчёт", callback_data="admin_preview"),
            InlineKeyboardButton(text="⏹ Завершить", callback_data="admin_finish"),
        ],
    ])


def unvoted_items_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Вернуть голосование", callback_data="admin_reopen")],
        [InlineKeyboardButton(text="➗ Разделить поровну", callback_data="admin_split_equal")],
        [InlineKeyboardButton(text="🗑 Убрать из счёта", callback_data="admin_remove_unvoted")],
    ])


def tip_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="0%", callback_data="tip:0"),
            InlineKeyboardButton(text="5%", callback_data="tip:5"),
            InlineKeyboardButton(text="10%", callback_data="tip:10"),
            InlineKeyboardButton(text="15%", callback_data="tip:15"),
        ],
        [InlineKeyboardButton(text="Другой %", callback_data="tip:custom")],
    ])


def settle_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Все рассчитались", callback_data="admin_settle")],
    ])
```

```python
# bot/keyboards/__init__.py
```

**Step 2: Commit**

```bash
git add bot/keyboards/
git commit -m "feat: inline keyboards — check, voting, admin controls"
```

---

## Task 7: Bot Entry Point + /start Handler

**Files:**
- Create: `bot/__main__.py`
- Create: `bot/handlers/__init__.py`
- Create: `bot/handlers/start.py`
- Create: `bot/middlewares.py`

**Step 1: Create DB session middleware**

```python
# bot/middlewares.py
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.db import async_session


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session() as session:
            data["db"] = session
            return await handler(event, data)
```

**Step 2: Create /start handler with deep link support**

```python
# bot/handlers/start.py
from aiogram import Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.session import SessionService

router = Router()


@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(message: Message, command: CommandObject, db: AsyncSession):
    """Handle /start with invite code (deep link join)."""
    invite_code = command.args
    svc = SessionService(db)
    member = await svc.join_session(
        invite_code=invite_code,
        user_tg_id=message.from_user.id,
        display_name=message.from_user.full_name,
    )
    if member is None:
        await message.answer("Сессия не найдена или вы уже участвуете.")
        return

    session = await svc.get_session_by_invite(invite_code)
    if session and session.status == "voting":
        # Show voting keyboard — handled in voting.py
        # For now, acknowledge join
        await message.answer(f"Вы присоединились к сессии! Выберите свои блюда.")
    else:
        await message.answer("Вы присоединились. Ожидайте начала голосования.")


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle plain /start."""
    await message.answer(
        "Привет! Я помогу разделить счёт.\n\n"
        "Отправьте фото чека, чтобы начать."
    )
```

**Step 3: Create `bot/handlers/__init__.py`** (empty)

**Step 4: Create `bot/__main__.py`**

```python
import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import settings
from bot.handlers import start, check, voting, admin
from bot.middlewares import DbSessionMiddleware

logging.basicConfig(level=logging.INFO)


async def main():
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.update.middleware(DbSessionMiddleware())

    dp.include_router(start.router)
    # dp.include_router(check.router)   # Task 8
    # dp.include_router(voting.router)   # Task 9
    # dp.include_router(admin.router)    # Task 10

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 5: Commit**

```bash
git add bot/__main__.py bot/handlers/ bot/middlewares.py
git commit -m "feat: bot entry point, /start handler with deep link join"
```

---

## Task 8: Check Photo Handler + OCR Flow

**Files:**
- Create: `bot/handlers/check.py`

**Step 1: Implement photo collection + OCR trigger**

```python
# bot/handlers/check.py
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.keyboards.check import ocr_result_kb, photo_collected_kb
from bot.services.ocr import OcrService
from bot.services.session import SessionService

router = Router()


class CheckStates(StatesGroup):
    collecting_photos = State()
    reviewing_ocr = State()
    editing_item = State()


@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext, db: AsyncSession):
    """Receive check photo(s)."""
    svc = SessionService(db)

    data = await state.get_data()
    session_id = data.get("session_id")

    if not session_id:
        session = await svc.create_session(admin_tg_id=message.from_user.id)
        session_id = str(session.id)
        await state.update_data(session_id=session_id)

    file_id = message.photo[-1].file_id  # highest resolution
    await svc.add_photo(session_id, tg_file_id=file_id)

    photo_count = data.get("photo_count", 0) + 1
    await state.update_data(photo_count=photo_count)
    await state.set_state(CheckStates.collecting_photos)

    await message.answer(
        f"Фото {photo_count} принято. Отправьте ещё или нажмите:",
        reply_markup=photo_collected_kb(),
    )


@router.callback_query(F.data == "ocr_start")
async def start_ocr(callback: CallbackQuery, state: FSMContext, db: AsyncSession, bot: Bot):
    """Download photos and run OCR."""
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)

    await callback.message.edit_text("⏳ Распознаю чек...")

    # Download photos
    photos_bytes = []
    for photo in session.photos:
        file = await bot.get_file(photo.tg_file_id)
        bio = await bot.download_file(file.file_path)
        photos_bytes.append(bio.read())

    # Run OCR
    ocr = OcrService(api_key=settings.openrouter_api_key, model=settings.openrouter_model)
    result = await ocr.parse_receipt(photos_bytes)

    # Save items
    items = await svc.save_ocr_items(
        session_id,
        [{"name": i.name, "price": i.price, "quantity": i.quantity} for i in result.items],
    )

    await svc.update_status(session_id, "voting")

    # Format result
    lines = ["📋 Распознанные позиции:\n"]
    for i, item in enumerate(result.items, 1):
        lines.append(f"{i}. {item.name} — {item.price}₽ (×{item.quantity})")

    if result.total_mismatch:
        items_sum = sum(i.price for i in result.items)
        lines.append(
            f"\n⚠️ Сумма позиций ({items_sum}₽) не совпадает с итогом чека ({result.total}₽)"
        )

    lines.append(f"\nИтого по чеку: {result.total}₽")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=ocr_result_kb(),
    )
    await state.set_state(CheckStates.reviewing_ocr)
```

Note: `svc.get_session_by_id` needs to be added to SessionService:

```python
# Add to bot/services/session.py:
async def get_session_by_id(self, session_id: UUID | str) -> Session | None:
    if isinstance(session_id, str):
        session_id = UUID(session_id)
    return await self._db.get(Session, session_id)
```

**Step 2: Commit**

```bash
git add bot/handlers/check.py bot/services/session.py
git commit -m "feat: check photo handler — multi-photo collection + OCR flow"
```

---

## Task 9: Voting Handler

**Files:**
- Create: `bot/handlers/voting.py`

**Step 1: Implement voting with inline buttons**

```python
# bot/handlers/voting.py
from uuid import UUID

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.voting import items_page_kb
from bot.services.session import SessionService

router = Router()


async def _send_voting_keyboard(
    callback: CallbackQuery, db: AsyncSession, session_id: str, user_tg_id: int, page: int = 0
):
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    user_votes = await svc.get_user_votes(session_id, user_tg_id)

    items_data = [
        {
            "id": item.id,
            "name": item.name,
            "price": item.price,
            "voter_count": len(item.votes),
        }
        for item in session.items
    ]

    kb = items_page_kb(items_data, user_votes, page=page)
    await callback.message.edit_text("Отметьте свои блюда:", reply_markup=kb)


@router.callback_query(F.data.startswith("vote:"))
async def handle_vote(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer()
    item_id = UUID(callback.data.split(":")[1])
    data = await state.get_data()
    session_id = data.get("session_id")
    page = data.get("vote_page", 0)

    svc = SessionService(db)
    await svc.toggle_vote(item_id, callback.from_user.id)

    await _send_voting_keyboard(callback, db, session_id, callback.from_user.id, page)


@router.callback_query(F.data.startswith("page:"))
async def handle_page(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer()
    page = int(callback.data.split(":")[1])
    await state.update_data(vote_page=page)
    data = await state.get_data()
    session_id = data["session_id"]

    await _send_voting_keyboard(callback, db, session_id, callback.from_user.id, page)


@router.callback_query(F.data == "vote_done")
async def handle_vote_done(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer("Ваш выбор сохранён!")
    await callback.message.edit_text("✅ Ваш выбор сохранён. Ожидайте итогов от админа.")


@router.callback_query(F.data == "missing_item")
async def handle_missing_item(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer()
    data = await state.get_data()
    session_id = data.get("session_id")

    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)

    # Notify admin
    from aiogram import Bot
    bot: Bot = callback.bot
    await bot.send_message(
        session.admin_tg_id,
        f"⚠️ {callback.from_user.full_name} не нашёл своё блюдо в списке!",
    )
    await callback.message.answer("Админ получил уведомление.")
```

Note: `svc.get_user_votes` needs to be added to SessionService:

```python
# Add to bot/services/session.py:
async def get_user_votes(self, session_id: UUID | str, user_tg_id: int) -> set[UUID]:
    if isinstance(session_id, str):
        session_id = UUID(session_id)
    result = await self._db.execute(
        select(ItemVote.item_id)
        .join(SessionItem)
        .where(SessionItem.session_id == session_id, ItemVote.user_tg_id == user_tg_id)
    )
    return set(result.scalars().all())
```

**Step 2: Commit**

```bash
git add bot/handlers/voting.py bot/services/session.py
git commit -m "feat: voting handler — inline buttons, pagination, missing item alert"
```

---

## Task 10: Admin Handler (Tips, Unvoted, Settlement)

**Files:**
- Create: `bot/handlers/admin.py`

**Step 1: Implement admin controls**

```python
# bot/handlers/admin.py
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin import settle_kb, tip_select_kb, unvoted_items_kb, voting_progress_kb
from bot.services.calculator import calculate_shares
from bot.services.session import SessionService

router = Router()


class AdminStates(StatesGroup):
    waiting_custom_tip = State()


@router.callback_query(F.data == "ocr_confirm")
async def confirm_ocr(callback: CallbackQuery, state: FSMContext, db: AsyncSession, bot: Bot):
    """Admin confirms OCR results → generate QR + invite link."""
    await callback.answer()
    import io
    import qrcode

    data = await state.get_data()
    session_id = data["session_id"]
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)

    bot_info = await bot.get_me()
    invite_url = f"https://t.me/{bot_info.username}?start={session.invite_code}"

    # Generate QR
    qr = qrcode.make(invite_url)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)

    from aiogram.types import BufferedInputFile

    await callback.message.answer_photo(
        BufferedInputFile(buf.read(), filename="qr.png"),
        caption=(
            f"📎 Ссылка для участников:\n{invite_url}\n\n"
            "Покажите QR-код или отправьте ссылку участникам."
        ),
    )
    await callback.message.answer(
        "Ожидаю участников...",
        reply_markup=voting_progress_kb(),
    )


@router.callback_query(F.data == "admin_preview")
async def preview_results(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]

    text = await _format_results(db, session_id, tip_percent=0)
    await callback.message.answer(f"📊 Предварительный расчёт (без чаевых):\n\n{text}")


@router.callback_query(F.data == "admin_finish")
async def finish_voting(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    unvoted = await svc.get_unvoted_items(session_id)

    if unvoted:
        lines = ["⚠️ Никто не отметил:"]
        for item in unvoted:
            lines.append(f"• {item.name} — {item.price}₽")
        await callback.message.edit_text("\n".join(lines), reply_markup=unvoted_items_kb())
    else:
        await callback.message.edit_text(
            "Выберите процент чаевых:", reply_markup=tip_select_kb()
        )


@router.callback_query(F.data == "admin_reopen")
async def reopen_voting(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer("Голосование продолжается.")
    await callback.message.edit_text("Голосование открыто.", reply_markup=voting_progress_kb())


@router.callback_query(F.data == "admin_split_equal")
async def split_unvoted_equal(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    """Assign unvoted items to all members equally."""
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    unvoted = await svc.get_unvoted_items(session_id)

    for item in unvoted:
        for member in session.members:
            await svc.toggle_vote(item.id, member.user_tg_id)

    await callback.message.edit_text("Выберите процент чаевых:", reply_markup=tip_select_kb())


@router.callback_query(F.data == "admin_remove_unvoted")
async def remove_unvoted(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    await svc.delete_unvoted_items(session_id)

    await callback.message.edit_text("Выберите процент чаевых:", reply_markup=tip_select_kb())


@router.callback_query(F.data.startswith("tip:"))
async def handle_tip(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    tip_value = callback.data.split(":")[1]
    if tip_value == "custom":
        await callback.answer()
        await callback.message.edit_text("Введите процент чаевых (число):")
        await state.set_state(AdminStates.waiting_custom_tip)
        return

    await callback.answer()
    tip_percent = int(tip_value)
    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    session.tip_percent = tip_percent
    await db.commit()

    text = await _format_results(db, session_id, tip_percent)
    await callback.message.edit_text(
        f"📊 Итоги сессии (чаевые {tip_percent}%):\n\n{text}",
        reply_markup=settle_kb(),
    )


@router.message(AdminStates.waiting_custom_tip)
async def handle_custom_tip(message: Message, state: FSMContext, db: AsyncSession):
    try:
        tip_percent = int(message.text.strip().replace("%", ""))
    except ValueError:
        await message.answer("Введите число (например: 12).")
        return

    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    session.tip_percent = tip_percent
    await db.commit()

    text = await _format_results(db, session_id, tip_percent)
    await message.answer(
        f"📊 Итоги сессии (чаевые {tip_percent}%):\n\n{text}",
        reply_markup=settle_kb(),
    )
    await state.clear()


@router.callback_query(F.data == "admin_settle")
async def settle_session(callback: CallbackQuery, state: FSMContext, db: AsyncSession, bot: Bot):
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    await svc.update_status(session_id, "closed")

    session = await svc.get_session_by_id(session_id)
    text = await _format_results(db, session_id, session.tip_percent)

    # Notify all members
    for member in session.members:
        share = await _get_user_share(db, session_id, member.user_tg_id, session.tip_percent)
        await bot.send_message(
            member.user_tg_id,
            f"✅ Сессия завершена!\nТвоя доля: {share}₽ (включая {session.tip_percent}% чаевых)",
        )

    await callback.message.edit_text(f"✅ Сессия закрыта!\n\n{text}")
    await state.clear()


async def _format_results(db: AsyncSession, session_id: str, tip_percent: int) -> str:
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)

    items_data = [
        {"price": item.price, "votes": [v.user_tg_id for v in item.votes]}
        for item in session.items
    ]
    shares = calculate_shares(items_data, tip_percent)

    members_map = {m.user_tg_id: m.display_name for m in session.members}
    # Include admin
    if session.admin_tg_id not in members_map:
        members_map[session.admin_tg_id] = "Админ"

    lines = []
    total = sum(shares.values())
    for user_id, amount in sorted(shares.items(), key=lambda x: -x[1]):
        name = members_map.get(user_id, f"User {user_id}")
        lines.append(f"{name} — {amount}₽")

    raw_total = sum(i.price for i in session.items)
    tip_amount = total - raw_total if tip_percent else 0

    lines.append("─" * 20)
    lines.append(f"Всего: {total}₽")
    if tip_percent:
        lines.append(f"(из них чаевые: {tip_amount}₽)")

    return "\n".join(lines)


async def _get_user_share(
    db: AsyncSession, session_id: str, user_tg_id: int, tip_percent: int
) -> int:
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    items_data = [
        {"price": item.price, "votes": [v.user_tg_id for v in item.votes]}
        for item in session.items
    ]
    shares = calculate_shares(items_data, tip_percent)
    return int(shares.get(user_tg_id, 0))
```

Note: `svc.delete_unvoted_items` needs to be added to SessionService:

```python
# Add to bot/services/session.py:
async def delete_unvoted_items(self, session_id: UUID | str) -> None:
    unvoted = await self.get_unvoted_items(session_id)
    for item in unvoted:
        await self._db.delete(item)
    await self._db.commit()
```

**Step 2: Uncomment routers in `bot/__main__.py`**

Uncomment the three `dp.include_router(...)` lines.

**Step 3: Commit**

```bash
git add bot/handlers/admin.py bot/services/session.py bot/__main__.py
git commit -m "feat: admin handler — QR generation, unvoted items, tips, settlement"
```

---

## Task 11: Telegram Stars Payment (Monetization)

**Files:**
- Create: `bot/services/quota.py`
- Create: `bot/handlers/payment.py`
- Test: `tests/test_quota.py`

**Step 1: Write the failing tests**

```python
# tests/test_quota.py
from datetime import datetime, timedelta, timezone

from bot.models.user_quota import UserQuota
from bot.services.quota import QuotaService


@pytest.fixture
def quota_svc(db_session):
    return QuotaService(db_session, free_limit=3)


async def test_new_user_has_quota(quota_svc):
    can_scan = await quota_svc.can_scan_free(user_tg_id=111)
    assert can_scan is True


async def test_use_quota(quota_svc, db_session):
    await quota_svc.use_free_scan(user_tg_id=111)
    quota = await db_session.get(UserQuota, 111)
    assert quota.free_scans_used == 1


async def test_exhaust_quota(quota_svc):
    for _ in range(3):
        await quota_svc.use_free_scan(user_tg_id=111)
    can_scan = await quota_svc.can_scan_free(user_tg_id=111)
    assert can_scan is False


async def test_quota_resets_monthly(quota_svc, db_session):
    quota = UserQuota(
        user_tg_id=111,
        free_scans_used=3,
        quota_reset_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(quota)
    await db_session.commit()

    can_scan = await quota_svc.can_scan_free(user_tg_id=111)
    assert can_scan is True
```

Note: add `import pytest` at top.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_quota.py -v`
Expected: FAIL

**Step 3: Implement quota service**

```python
# bot/services/quota.py
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user_quota import UserQuota


def _next_month_start() -> datetime:
    now = datetime.now(timezone.utc)
    if now.month == 12:
        return now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


class QuotaService:
    def __init__(self, db: AsyncSession, free_limit: int):
        self._db = db
        self._free_limit = free_limit

    async def _get_or_create(self, user_tg_id: int) -> UserQuota:
        quota = await self._db.get(UserQuota, user_tg_id)
        if quota is None:
            quota = UserQuota(
                user_tg_id=user_tg_id,
                free_scans_used=0,
                quota_reset_at=_next_month_start(),
            )
            self._db.add(quota)
            await self._db.commit()
            await self._db.refresh(quota)
        return quota

    async def can_scan_free(self, user_tg_id: int) -> bool:
        quota = await self._get_or_create(user_tg_id)
        now = datetime.now(timezone.utc)
        if now >= quota.quota_reset_at:
            quota.free_scans_used = 0
            quota.quota_reset_at = _next_month_start()
            await self._db.commit()
        return quota.free_scans_used < self._free_limit

    async def use_free_scan(self, user_tg_id: int) -> None:
        quota = await self._get_or_create(user_tg_id)
        quota.free_scans_used += 1
        await self._db.commit()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_quota.py -v`
Expected: all 4 tests PASS

**Step 5: Implement payment handler**

```python
# bot/handlers/payment.py
from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.models.payment import Payment
from bot.services.quota import QuotaService

router = Router()


@router.callback_query(F.data == "pay_stars")
async def request_payment(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer_invoice(
        title="Распознавание чека",
        description="Оплата за OCR-распознавание одного чека",
        payload="scan_payment",
        currency="XTR",
        prices=[LabeledPrice(label="Сканирование чека", amount=settings.scan_price_stars)],
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, db: AsyncSession):
    payment = Payment(
        user_tg_id=message.from_user.id,
        session_id=None,  # will be linked when OCR starts
        stars_amount=message.successful_payment.total_amount,
        telegram_charge_id=message.successful_payment.telegram_payment_charge_id,
    )
    db.add(payment)
    await db.commit()

    await message.answer("✅ Оплата прошла! Теперь отправьте фото чека.")
```

Note: `Payment.session_id` needs to be nullable — update the model:

```python
# In bot/models/payment.py, change:
session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sessions.id"), nullable=True)
```

**Step 6: Wire payment router into `bot/__main__.py`**

Add `from bot.handlers import payment` and `dp.include_router(payment.router)`.

**Step 7: Integrate quota check into check handler**

In `bot/handlers/check.py`, before OCR, add quota check:

```python
# In handle_photo or start_ocr, before calling OCR:
quota_svc = QuotaService(db, settings.free_scans_per_month)
if not await quota_svc.can_scan_free(callback.from_user.id):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ Оплатить {settings.scan_price_stars} Stars", callback_data="pay_stars")]
    ])
    await callback.message.edit_text(
        f"Бесплатный лимит исчерпан ({settings.free_scans_per_month}/мес).",
        reply_markup=kb,
    )
    return
await quota_svc.use_free_scan(callback.from_user.id)
```

**Step 8: Commit**

```bash
git add bot/services/quota.py bot/handlers/payment.py bot/models/payment.py tests/test_quota.py bot/__main__.py bot/handlers/check.py
git commit -m "feat: monetization — freemium quota + Telegram Stars payment"
```

---

## Task 12: Item Editing (Admin)

**Files:**
- Modify: `bot/handlers/check.py` (add edit flow)

**Step 1: Add edit callbacks to check handler**

```python
# Add to bot/handlers/check.py:

@router.callback_query(F.data == "ocr_edit")
async def start_edit(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    """Show items list with edit/delete buttons."""
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)

    buttons = []
    for item in session.items:
        buttons.append([
            InlineKeyboardButton(
                text=f"{item.name} — {item.price}₽",
                callback_data=f"edit_item:{item.id}",
            ),
            InlineKeyboardButton(text="🗑", callback_data=f"del_item:{item.id}"),
        ])
    buttons.append([InlineKeyboardButton(text="➕ Добавить позицию", callback_data="add_item")])
    buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data="ocr_confirm")])

    from aiogram.types import InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Редактирование позиций:", reply_markup=kb)


@router.callback_query(F.data.startswith("del_item:"))
async def delete_item(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    from uuid import UUID
    item_id = UUID(callback.data.split(":")[1])
    svc = SessionService(db)
    await svc.delete_item(item_id)
    await callback.answer("Удалено")
    await start_edit(callback, state, db)


@router.callback_query(F.data.startswith("edit_item:"))
async def edit_item_prompt(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.split(":")[1]
    await state.update_data(editing_item_id=item_id)
    await state.set_state(CheckStates.editing_item)
    await callback.answer()
    await callback.message.edit_text(
        'Введите новое название и цену через дефис:\nНапример: Пицца Маргарита - 700'
    )


@router.message(CheckStates.editing_item)
async def handle_edit_item(message: Message, state: FSMContext, db: AsyncSession):
    from uuid import UUID
    from decimal import Decimal

    data = await state.get_data()
    item_id = UUID(data["editing_item_id"])

    try:
        name, price_str = message.text.rsplit("-", 1)
        name = name.strip()
        price = Decimal(price_str.strip())
    except (ValueError, InvalidOperation):
        await message.answer('Неверный формат. Пример: Пицца Маргарита - 700')
        return

    svc = SessionService(db)
    await svc.update_item(item_id, name=name, price=price)
    await state.set_state(CheckStates.reviewing_ocr)
    await message.answer(f"✅ Обновлено: {name} — {price}₽")


@router.callback_query(F.data == "add_item")
async def add_item_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CheckStates.editing_item)
    await state.update_data(editing_item_id=None)
    await callback.answer()
    await callback.message.edit_text(
        'Введите название и цену через дефис:\nНапример: Тирамису - 380'
    )
```

Note: add `update_item` and `delete_item` to SessionService:

```python
# Add to bot/services/session.py:
async def delete_item(self, item_id: UUID) -> None:
    item = await self._db.get(SessionItem, item_id)
    if item:
        await self._db.delete(item)
        await self._db.commit()

async def update_item(self, item_id: UUID, name: str, price: Decimal) -> None:
    item = await self._db.get(SessionItem, item_id)
    if item:
        item.name = name
        item.price = price
        await self._db.commit()
```

Also handle `editing_item_id=None` case (new item) in `handle_edit_item`:

```python
# In handle_edit_item, after parsing name/price:
if data.get("editing_item_id") is None:
    session_id = data["session_id"]
    await svc.save_ocr_items(session_id, [{"name": name, "price": price, "quantity": 1}])
    await message.answer(f"✅ Добавлено: {name} — {price}₽")
else:
    await svc.update_item(item_id, name=name, price=price)
    await message.answer(f"✅ Обновлено: {name} — {price}₽")
```

**Step 2: Commit**

```bash
git add bot/handlers/check.py bot/services/session.py
git commit -m "feat: item editing — add, edit, delete receipt items"
```

---

## Task 13: CLAUDE.md + Final Wiring

**Files:**
- Create: `CLAUDE.md`

**Step 1: Create CLAUDE.md**

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Telegram bot for splitting restaurant bills. Users photograph receipts, LLM (via OpenRouter) extracts items, participants vote on their dishes via inline keyboards, bot calculates shares.

## Commands

```bash
# Run bot locally
python -m bot

# Run tests
pytest
pytest tests/test_calculator.py -v          # single file
pytest tests/test_calculator.py::test_name  # single test

# Lint
ruff check bot/ tests/
ruff format bot/ tests/

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head

# Docker
docker compose up --build
```

## Architecture

Monolith: aiogram 3.x (long polling) + SQLAlchemy 2.x (async) + PostgreSQL.

- `bot/handlers/` — aiogram routers (start, check, voting, admin, payment)
- `bot/services/` — business logic (ocr, session, calculator, quota)
- `bot/models/` — SQLAlchemy ORM models
- `bot/keyboards/` — inline keyboard factories
- `bot/config.py` — pydantic-settings from env
- `bot/middlewares.py` — DB session injection middleware
- `bot/db.py` — async engine + sessionmaker

Virtual sessions (not real TG groups): users interact with bot in DMs, linked by invite_code deep links.

## Key Patterns

- All DB access is async (asyncpg + SQLAlchemy async session)
- DB session injected via aiogram middleware → `db: AsyncSession` parameter in handlers
- FSM (finite state machine) via aiogram for multi-step flows (photo collection, editing)
- Tests use in-memory SQLite (aiosqlite) via conftest fixture
- OpenRouter API (OpenAI-compatible) for LLM OCR — model configurable via env
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md for Claude Code guidance"
```

---

## Summary

| Task | What | Tests |
|------|------|-------|
| 1 | Project scaffolding | — |
| 2 | DB models + Alembic | 4 tests |
| 3 | Calculator service | 7 tests |
| 4 | OCR service (OpenRouter) | 3 tests |
| 5 | Session service | 8 tests |
| 6 | Inline keyboards | — |
| 7 | Bot entry + /start | — |
| 8 | Check photo + OCR flow | — |
| 9 | Voting handler | — |
| 10 | Admin handler | — |
| 11 | Monetization (quota + Stars) | 4 tests |
| 12 | Item editing | — |
| 13 | CLAUDE.md | — |

**Total: 13 tasks, 26 tests**
