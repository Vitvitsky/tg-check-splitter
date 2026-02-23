"""Tests for API Pydantic schemas."""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from api.schemas import ItemIn, SessionOut, TipIn


class TestTipInValidation:
    """TipIn accepts 0–100, rejects values outside that range."""

    def test_accepts_zero(self) -> None:
        tip = TipIn(tip_percent=0)
        assert tip.tip_percent == 0

    def test_accepts_hundred(self) -> None:
        tip = TipIn(tip_percent=100)
        assert tip.tip_percent == 100

    def test_accepts_midrange(self) -> None:
        tip = TipIn(tip_percent=15)
        assert tip.tip_percent == 15

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValidationError):
            TipIn(tip_percent=-1)

    def test_rejects_over_hundred(self) -> None:
        with pytest.raises(ValidationError):
            TipIn(tip_percent=101)


class TestItemInValidation:
    """ItemIn rejects invalid names and prices."""

    def test_valid_item(self) -> None:
        item = ItemIn(name="Salad", price=9.99)
        assert item.name == "Salad"
        assert item.price == 9.99
        assert item.quantity == 1  # default

    def test_rejects_zero_price(self) -> None:
        with pytest.raises(ValidationError):
            ItemIn(name="Salad", price=0)

    def test_rejects_negative_price(self) -> None:
        with pytest.raises(ValidationError):
            ItemIn(name="Salad", price=-5.0)

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(ValidationError):
            ItemIn(name="", price=10.0)

    def test_rejects_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            ItemIn(name="A" * 201, price=10.0)

    def test_quantity_default_is_one(self) -> None:
        item = ItemIn(name="Bread", price=3.0)
        assert item.quantity == 1

    def test_rejects_zero_quantity(self) -> None:
        with pytest.raises(ValidationError):
            ItemIn(name="Bread", price=3.0, quantity=0)


class TestSessionOutUuidSerialization:
    """SessionOut converts UUID fields from ORM objects to strings."""

    def test_uuid_to_str(self) -> None:
        session_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # Simulate an ORM-like object using SimpleNamespace
        fake_session = SimpleNamespace(
            id=session_id,
            admin_tg_id=123456789,
            invite_code="abc123",
            status="created",
            currency="RUB",
            tip_percent=0,
            created_at=now,
            closed_at=None,
            photos=[],
            items=[],
            members=[],
        )

        out = SessionOut.model_validate(fake_session, from_attributes=True)

        assert out.id == str(session_id)
        assert isinstance(out.id, str)

    def test_nested_uuid_serialization(self) -> None:
        session_id = uuid.uuid4()
        photo_id = uuid.uuid4()
        item_id = uuid.uuid4()
        vote_id = uuid.uuid4()
        member_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        fake_vote = SimpleNamespace(
            id=vote_id,
            item_id=item_id,
            user_tg_id=111,
            quantity=2,
        )
        fake_item = SimpleNamespace(
            id=item_id,
            name="Pizza",
            price=15.50,
            quantity=1,
            votes=[fake_vote],
        )
        fake_photo = SimpleNamespace(
            id=photo_id,
            tg_file_id="AgACAgIAAxk",
            created_at=now,
        )
        fake_member = SimpleNamespace(
            id=member_id,
            user_tg_id=111,
            display_name="Alice",
            tip_percent=10,
            confirmed=True,
            joined_at=now,
        )
        fake_session = SimpleNamespace(
            id=session_id,
            admin_tg_id=111,
            invite_code="xyz789",
            status="voting",
            currency="USD",
            tip_percent=10,
            created_at=now,
            closed_at=None,
            photos=[fake_photo],
            items=[fake_item],
            members=[fake_member],
        )

        out = SessionOut.model_validate(fake_session, from_attributes=True)

        # All UUID fields should be strings
        assert out.id == str(session_id)
        assert out.photos[0].id == str(photo_id)
        assert out.items[0].id == str(item_id)
        assert out.items[0].votes[0].id == str(vote_id)
        assert out.items[0].votes[0].item_id == str(item_id)
        assert out.members[0].id == str(member_id)

    def test_json_serialization(self) -> None:
        session_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        fake_session = SimpleNamespace(
            id=session_id,
            admin_tg_id=123456789,
            invite_code="abc123",
            status="created",
            currency="RUB",
            tip_percent=0,
            created_at=now,
            closed_at=None,
            photos=[],
            items=[],
            members=[],
        )

        out = SessionOut.model_validate(fake_session, from_attributes=True)
        json_str = out.model_dump_json()

        assert str(session_id) in json_str
