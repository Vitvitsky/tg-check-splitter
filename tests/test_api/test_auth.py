"""Tests for Telegram Mini App initData HMAC-SHA256 authentication."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from api.auth import TelegramUser, _parse_telegram_user, validate_init_data

TEST_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"


def make_init_data(
    user_id: int = 12345,
    first_name: str = "Test",
    auth_date: int | None = None,
    **user_kwargs: object,
) -> str:
    """Build a valid Telegram Mini App initData string for testing."""
    user = {"id": user_id, "first_name": first_name, **user_kwargs}
    params = {
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "test_query_id",
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", TEST_BOT_TOKEN.encode(), hashlib.sha256).digest()
    hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = hash_value
    return urlencode(params)


class TestValidateInitData:
    """Tests for ``validate_init_data``."""

    def test_valid_init_data(self) -> None:
        init_data = make_init_data()
        result = validate_init_data(init_data, TEST_BOT_TOKEN)

        assert "user" in result
        assert "auth_date" in result
        assert "query_id" in result
        # hash must be stripped from the returned dict
        assert "hash" not in result

    def test_invalid_hash(self) -> None:
        init_data = make_init_data()
        # Tamper with the hash
        init_data = init_data.replace("hash=", "hash=0000")

        with pytest.raises(ValueError, match="Invalid initData hash"):
            validate_init_data(init_data, TEST_BOT_TOKEN)

    def test_missing_hash(self) -> None:
        params = {
            "user": json.dumps({"id": 1, "first_name": "X"}),
            "auth_date": str(int(time.time())),
        }
        init_data = urlencode(params)

        with pytest.raises(ValueError, match="Missing hash"):
            validate_init_data(init_data, TEST_BOT_TOKEN)

    def test_expired_init_data(self) -> None:
        expired_ts = int(time.time()) - 86401  # just over 24 h ago
        init_data = make_init_data(auth_date=expired_ts)

        with pytest.raises(ValueError, match="expired"):
            validate_init_data(init_data, TEST_BOT_TOKEN)

    def test_wrong_bot_token(self) -> None:
        init_data = make_init_data()
        with pytest.raises(ValueError, match="Invalid initData hash"):
            validate_init_data(init_data, "wrong:token")

    def test_user_json_preserved(self) -> None:
        init_data = make_init_data(user_id=99, first_name="Alice", last_name="Smith")
        result = validate_init_data(init_data, TEST_BOT_TOKEN)
        user_data = json.loads(result["user"])

        assert user_data["id"] == 99
        assert user_data["first_name"] == "Alice"
        assert user_data["last_name"] == "Smith"


class TestParseTelegramUser:
    """Tests for ``_parse_telegram_user`` / TelegramUser dataclass."""

    def test_parse_telegram_user_full(self) -> None:
        user_json = json.dumps(
            {
                "id": 42,
                "first_name": "Bob",
                "last_name": "Jones",
                "username": "bobjones",
                "language_code": "en",
                "photo_url": "https://t.me/photo.jpg",
            }
        )
        user = _parse_telegram_user(user_json)

        assert user == TelegramUser(
            id=42,
            first_name="Bob",
            last_name="Jones",
            username="bobjones",
            language_code="en",
            photo_url="https://t.me/photo.jpg",
        )

    def test_parse_telegram_user_minimal(self) -> None:
        user_json = json.dumps({"id": 1, "first_name": "X"})
        user = _parse_telegram_user(user_json)

        assert user.id == 1
        assert user.first_name == "X"
        assert user.last_name is None
        assert user.username is None
        assert user.language_code is None
        assert user.photo_url is None

    def test_parse_telegram_user_missing_required_field(self) -> None:
        user_json = json.dumps({"first_name": "NoId"})
        with pytest.raises(KeyError):
            _parse_telegram_user(user_json)
