"""Push notifications via Telegram Bot API (no aiogram dependency)."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class NotificationService:
    """Sends Telegram messages via Bot API using httpx."""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
    ) -> bool:
        """Send a message. Returns True on success, False on failure (never raises)."""
        payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{self.base_url}/sendMessage", json=payload)
                resp.raise_for_status()
                return True
        except Exception:
            logger.warning("Failed to send notification to %s", chat_id, exc_info=True)
            return False

    async def notify_settle(
        self,
        members: list[dict],
        shares: dict[int, float],
        currency: str,
        webapp_url: str,
        invite_code: str,
    ) -> None:
        """Notify all members about settlement with their personal share."""
        for member in members:
            uid = member["user_tg_id"]
            share = shares.get(uid, 0)
            text = f"Чек рассчитан! Ваша доля: {share:.0f} {currency}"
            reply_markup = {
                "inline_keyboard": [
                    [
                        {
                            "text": "Посмотреть детали",
                            "web_app": {"url": f"{webapp_url}?startapp={invite_code}"},
                        }
                    ]
                ]
            }
            await self.send_message(uid, text, reply_markup)

    async def notify_member_joined(
        self,
        admin_tg_id: int,
        member_name: str,
    ) -> None:
        """Notify admin when a new member joins."""
        text = f"{member_name} присоединился к чеку"
        await self.send_message(admin_tg_id, text)
