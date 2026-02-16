from aiogram import Bot, F, Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.voting import send_voting_keyboard_to_user
from bot.keyboards.check import MAIN_MENU_BTN, main_menu_kb
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
        await message.answer("Сессия не найдена или вы уже участвуете.")
        return

    session = await svc.get_session_by_invite(invite_code)
    await state.update_data(session_id=str(session.id))

    if session and session.status == "voting":
        await message.answer("Вы присоединились к сессии! Выберите свои блюда.")
        await send_voting_keyboard_to_user(bot, db, message.from_user.id, str(session.id))
    else:
        await message.answer("Вы присоединились. Ожидайте начала голосования.")


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle plain /start."""
    await message.answer(
        "Привет! Я помогу разделить счёт.\n\n"
        "Отправьте фото чека, чтобы начать.",
        reply_markup=main_menu_kb(),
    )


@router.message(F.text == MAIN_MENU_BTN)
async def main_menu_btn(message: Message):
    """Handle main menu button press."""
    await message.answer("Отправьте фото чека, чтобы начать.")
