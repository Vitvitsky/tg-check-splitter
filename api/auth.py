"""Telegram Mini App initData HMAC-SHA256 authentication."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qs

from fastapi import Depends, HTTPException, Request

from bot.config import get_settings

_MAX_AUTH_AGE_SECONDS = 86400  # 24 hours


@dataclass(frozen=True, slots=True)
class TelegramUser:
    """Authenticated Telegram user extracted from initData."""

    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    photo_url: str | None = None


def validate_init_data(init_data: str, bot_token: str) -> dict[str, str]:
    """Validate Telegram Mini App *initData* using HMAC-SHA256.

    Parameters
    ----------
    init_data:
        URL-encoded string sent by the Telegram Mini App client.
    bot_token:
        The bot token used to derive the secret key.

    Returns
    -------
    dict[str, str]
        Parsed key-value pairs from *init_data* (excluding ``hash``).

    Raises
    ------
    ValueError
        If the hash is missing, does not match, or ``auth_date`` is too old.
    """
    parsed = parse_qs(init_data, keep_blank_values=True)
    # parse_qs returns lists — flatten to single values
    params: dict[str, str] = {k: v[0] for k, v in parsed.items()}

    received_hash = params.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing hash in initData")

    # Build data-check-string: sorted key=value pairs joined by \n
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

    # secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()

    # computed_hash = HMAC_SHA256(key=secret_key, msg=data_check_string)
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("Invalid initData hash")

    # Check auth_date freshness
    auth_date_str = params.get("auth_date")
    if auth_date_str is None:
        raise ValueError("Missing auth_date in initData")

    try:
        auth_date = int(auth_date_str)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid auth_date in initData") from exc

    if time.time() - auth_date > _MAX_AUTH_AGE_SECONDS:
        raise ValueError("initData has expired")

    return params


def _parse_telegram_user(user_json: str) -> TelegramUser:
    """Parse the ``user`` JSON string into a :class:`TelegramUser`."""
    data = json.loads(user_json)
    return TelegramUser(
        id=data["id"],
        first_name=data["first_name"],
        last_name=data.get("last_name"),
        username=data.get("username"),
        language_code=data.get("language_code"),
        photo_url=data.get("photo_url"),
    )


async def get_current_user(request: Request) -> TelegramUser:
    """FastAPI dependency: authenticate via Telegram Mini App *initData*.

    Expects an ``Authorization`` header in the format::

        tma <initData>

    Returns a :class:`TelegramUser` on success; raises ``HTTPException(401)``
    otherwise.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = auth_header.split(" ", maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "tma":
        raise HTTPException(
            status_code=401,
            detail="Authorization header must use 'tma <initData>' format",
        )

    init_data = parts[1]

    try:
        bot_token = get_settings().bot_token
        params = validate_init_data(init_data, bot_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_json = params.get("user")
    if not user_json:
        raise HTTPException(status_code=401, detail="No user data in initData")

    try:
        return _parse_telegram_user(user_json)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=401, detail=f"Invalid user data: {exc}") from exc


# Convenience type alias for use in route signatures
CurrentUser = Depends(get_current_user)
