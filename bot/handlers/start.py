from aiogram import Bot, F, Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _, lazy_gettext as __
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.handlers.voting import send_voting_keyboard_to_user
from bot.keyboards.check import main_menu_kb, webapp_button_kb
from bot.services.quota import QuotaService
from bot.services.session import SessionService

router = Router()


@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(
    message: Message, command: CommandObject, state: FSMContext, db: AsyncSession, bot: Bot
):
    """Handle /start with invite code (deep link join)."""
    invite_code = command.args
    svc = SessionService(db)
    member = await svc.join_session(
        invite_code=invite_code,
        user_tg_id=message.from_user.id,
        display_name=message.from_user.full_name,
    )
    if member is None:
        await message.answer(_("Session not found"))
        return

    session = await svc.get_session_by_invite(invite_code)
    await state.update_data(session_id=str(session.id))

    settings = get_settings()
    webapp_url = f"{settings.webapp_url}?startapp={invite_code}"

    if session and session.status == "voting":
        await message.answer(_("Joined voting"))
        await send_voting_keyboard_to_user(
            bot,
            db,
            message.from_user.id,
            str(session.id),
            locale=message.from_user.language_code,
        )
    else:
        await message.answer(_("Joined waiting"))

    await message.answer(
        _("Open check in Mini App"),
        reply_markup=webapp_button_kb(webapp_url, text="Перейти к чеку"),
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle plain /start."""
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
    """Handle main menu button press."""
    await message.answer(_("Send photo to start"))


@router.message(F.text == __("My quota"))
async def quota_btn(message: Message, db: AsyncSession):
    """Show user's scan quota."""
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
