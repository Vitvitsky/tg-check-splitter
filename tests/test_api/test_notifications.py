"""Tests for push notification service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.notifications import NotificationService


@pytest.fixture
def notifier():
    return NotificationService("fake:token")


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_send_message_success(self, notifier):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await notifier.send_message(123, "Hello")
            assert result is True
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_reply_markup(self, notifier):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            markup = {"inline_keyboard": [[{"text": "Click", "url": "https://example.com"}]]}
            result = await notifier.send_message(123, "Hello", reply_markup=markup)
            assert result is True

            call_kwargs = mock_client.post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
            assert payload["reply_markup"] == markup

    @pytest.mark.asyncio
    async def test_send_message_failure(self, notifier):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("Network error"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await notifier.send_message(123, "Hello")
            assert result is False


class TestNotifySettle:
    @pytest.mark.asyncio
    async def test_notify_settle(self, notifier):
        notifier.send_message = AsyncMock(return_value=True)
        members = [
            {"user_tg_id": 111, "display_name": "Alice"},
            {"user_tg_id": 222, "display_name": "Bob"},
        ]
        shares = {111: 500.0, 222: 300.0}
        await notifier.notify_settle(members, shares, "RUB", "https://app.example.com", "abc123")
        assert notifier.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_notify_settle_includes_share_amount(self, notifier):
        notifier.send_message = AsyncMock(return_value=True)
        members = [{"user_tg_id": 111, "display_name": "Alice"}]
        shares = {111: 500.0}
        await notifier.notify_settle(members, shares, "RUB", "https://app.example.com", "abc123")
        call_args = notifier.send_message.call_args
        text = call_args[0][1]
        assert "500" in text
        assert "RUB" in text

    @pytest.mark.asyncio
    async def test_notify_settle_missing_share_defaults_to_zero(self, notifier):
        notifier.send_message = AsyncMock(return_value=True)
        members = [{"user_tg_id": 999, "display_name": "Ghost"}]
        shares = {}  # no share for this user
        await notifier.notify_settle(members, shares, "RUB", "https://app.example.com", "abc123")
        call_args = notifier.send_message.call_args
        text = call_args[0][1]
        assert "0" in text


class TestNotifyMemberJoined:
    @pytest.mark.asyncio
    async def test_notify_member_joined(self, notifier):
        notifier.send_message = AsyncMock(return_value=True)
        await notifier.notify_member_joined(admin_tg_id=111, member_name="Bob")
        notifier.send_message.assert_called_once_with(111, "Bob присоединился к чеку")
