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
        await message.answer("Вы присоединились к сессии! Выберите свои блюда.")
    else:
        await message.answer("Вы присоединились. Ожидайте начала голосования.")


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle plain /start."""
    await message.answer(
        "Привет! Я помогу разделить счёт.\n\n"
        "Отправьте фото чека, чтобы начать."
    )
