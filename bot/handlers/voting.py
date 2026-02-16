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

    bot: Bot = callback.bot
    await bot.send_message(
        session.admin_tg_id,
        f"⚠️ {callback.from_user.full_name} не нашёл своё блюдо в списке!",
    )
    await callback.message.answer("Админ получил уведомление.")
