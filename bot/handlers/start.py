"""Entry points into the Mini App.

The bot is deliberately thin: the Mini App owns scanning, editing, voting, tips and
settlement. Everything here does one of three things — greet, hand an invite off to
the Mini App, or answer a question that is cheaper to answer in chat than to open an
app for. There is no FSM and no inline voting flow; those used to live in
bot/handlers/{check,voting,admin}.py and duplicated the REST API in api/ line for line.
"""

import logging

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _, lazy_gettext as __
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from bot.keyboards.check import main_menu_kb, webapp_button_kb
from core.services.quota import QuotaService
from core.services.session import SessionService

logger = logging.getLogger(__name__)
router = Router()


def session_url(invite_code: str) -> str:
    """Direct Mini App URL for a session.

    A real client-side route rather than `?startapp=`: the API serves index.html for
    unknown paths (see api/app.py), so this lands straight on the join screen. The
    old form passed `?startapp=` to a web_app button and nothing in the frontend ever
    read that parameter — participants were dropped on the home screen instead.
    """
    return f"{get_settings().webapp_url}/session/{invite_code}"


@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(message: Message, command: CommandObject, db: AsyncSession):
    """Handle /start <invite_code> — legacy t.me/<bot>?start=<code> invite links.

    Newly generated invites use ?startapp= and open the Mini App directly without
    touching the bot. Links already shared with `?start=` still have to work, so the
    join is performed here and the user is handed straight to the Mini App.
    """
    invite_code = command.args
    logger.info("user_id=%s deep_link=%s", message.from_user.id, invite_code)

    svc = SessionService(db)
    session = await svc.get_session_by_invite(invite_code)
    if session is None:
        await message.answer(_("Session not found"))
        return

    # join_session() returns None when the user is already a member — not an error.
    await svc.join_session(
        invite_code=invite_code,
        user_tg_id=message.from_user.id,
        display_name=message.from_user.full_name,
    )

    await message.answer(
        _("Joined waiting"),
        reply_markup=webapp_button_kb(session_url(invite_code), text=_("Open check")),
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle plain /start."""
    logger.info("user_id=%s /start", message.from_user.id)
    settings = get_settings()
    await message.answer(
        _("Start greeting") + "\n\n" + _("Send photo to start"),
        reply_markup=main_menu_kb(_),
    )
    await message.answer(
        _("Or open Mini App"),
        reply_markup=webapp_button_kb(settings.webapp_url),
    )


@router.message(F.text == __("Split check"))
async def main_menu_btn(message: Message):
    """Open the Mini App on the scan screen."""
    settings = get_settings()
    await message.answer(
        _("Send photo to start"),
        reply_markup=webapp_button_kb(f"{settings.webapp_url}/scan", text=_("Open check")),
    )


@router.message(F.text == __("My quota"))
async def quota_btn(message: Message, db: AsyncSession):
    """Show user's scan quota."""
    logger.info("user_id=%s quota check", message.from_user.id)
    settings = get_settings()
    quota_svc = QuotaService(db, settings.free_scans_per_month)
    free_left, paid_scans, reset_at = await quota_svc.get_quota_info(message.from_user.id)

    reset_str = reset_at.strftime("%d.%m.%Y")
    lines = [
        _("Free quota").format(free_left=free_left, limit=settings.free_scans_per_month),
        _("Paid scans").format(paid=paid_scans),
        _("Reset date").format(date=reset_str),
    ]
    await message.answer("\n".join(lines))


@router.message(F.text == __("Help"))
async def help_btn(message: Message):
    """Show help instructions."""
    await message.answer(_("Help text"))


@router.message(F.photo)
async def photo_hint(message: Message):
    """Photos used to start an in-chat OCR flow; scanning now lives in the Mini App."""
    settings = get_settings()
    await message.answer(
        _("Send photo to start"),
        reply_markup=webapp_button_kb(f"{settings.webapp_url}/scan", text=_("Open check")),
    )
