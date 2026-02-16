from uuid import UUID

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.voting import items_page_kb, participant_summary_kb, participant_tip_kb
from bot.services.calculator import calculate_user_share
from bot.services.session import SessionService

router = Router()


class VotingStates(StatesGroup):
    custom_tip = State()


async def _build_voting_keyboard(db: AsyncSession, session_id: str, user_tg_id: int, page: int = 0):
    """Build voting keyboard markup and return (text, kb)."""
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    user_votes = await svc.get_user_votes(session_id, user_tg_id)

    items_data = [
        {
            "id": item.id,
            "name": item.name,
            "price": item.price,
            "quantity": item.quantity,
            "total_claimed": sum(v.quantity for v in item.votes),
        }
        for item in session.items
    ]

    kb = items_page_kb(items_data, user_votes, page=page)
    return "Отметьте свои блюда:", kb


async def _send_voting_keyboard(
    callback: CallbackQuery, db: AsyncSession, session_id: str, user_tg_id: int, page: int = 0
):
    text, kb = await _build_voting_keyboard(db, session_id, user_tg_id, page)
    await callback.message.edit_text(text, reply_markup=kb)


async def send_voting_keyboard_to_user(
    bot: Bot, db: AsyncSession, user_tg_id: int, session_id: str, page: int = 0
):
    """Send voting keyboard as a new message to a user (not via callback edit)."""
    text, kb = await _build_voting_keyboard(db, session_id, user_tg_id, page)
    await bot.send_message(user_tg_id, text, reply_markup=kb)


async def _build_summary_text(db: AsyncSession, session_id: str, user_tg_id: int, tip_percent: int) -> str:
    """Build personal summary text for a participant."""
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    user_votes = await svc.get_user_votes(session_id, user_tg_id)

    items_data = [
        {
            "price": item.price,
            "quantity": item.quantity,
            "votes": {v.user_tg_id: v.quantity for v in item.votes},
        }
        for item in session.items
    ]

    dishes_total, tip_amount, grand_total = calculate_user_share(items_data, user_tg_id, tip_percent)

    from decimal import Decimal
    lines = ["🧾 Ваши блюда:\n"]
    for item in session.items:
        my_qty = user_votes.get(item.id, 0)
        if my_qty:
            per_unit = item.price / Decimal(item.quantity) if item.quantity else item.price
            cost = per_unit * my_qty
            if item.quantity > 1:
                lines.append(f"  {item.name} ×{my_qty} — {int(cost)}₽ (из {item.price}₽ за {item.quantity} шт)")
            else:
                lines.append(f"  {item.name} — {int(item.price)}₽")

    lines.append(f"\nСумма блюд: {int(dishes_total)}₽")
    lines.append(f"Чаевые {tip_percent}%: {int(tip_amount)}₽")
    lines.append(f"\n💰 Итого: {int(grand_total)}₽")

    return "\n".join(lines)


# --- Voting ---

@router.callback_query(F.data.startswith("vote:"))
async def handle_vote(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer()
    item_id = UUID(callback.data.split(":")[1])
    data = await state.get_data()
    session_id = data.get("session_id")
    page = data.get("vote_page", 0)

    svc = SessionService(db)
    # Get item to know max quantity
    from bot.models.session import SessionItem
    item = await db.get(SessionItem, item_id)
    max_qty = item.quantity if item else 1
    await svc.cycle_vote(item_id, callback.from_user.id, max_qty)
    # Reset confirmation since dishes changed
    await svc.unconfirm_member(session_id, callback.from_user.id)

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
    """After selecting dishes -> show tip selection."""
    await callback.answer()
    data = await state.get_data()
    session_id = data.get("session_id")

    # Check that user selected at least one dish
    svc = SessionService(db)
    user_votes = await svc.get_user_votes(session_id, callback.from_user.id)
    if not user_votes:
        await callback.answer("Выберите хотя бы одно блюдо!", show_alert=True)
        return

    await callback.message.edit_text(
        "Выберите процент чаевых:",
        reply_markup=participant_tip_kb(),
    )


# --- Tip selection ---

@router.callback_query(F.data.startswith("ptip:"))
async def handle_participant_tip(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    tip_value = callback.data.split(":")[1]

    if tip_value == "back":
        # Go back to dish selection
        await callback.answer()
        data = await state.get_data()
        session_id = data["session_id"]
        page = data.get("vote_page", 0)
        await _send_voting_keyboard(callback, db, session_id, callback.from_user.id, page)
        return

    if tip_value == "custom":
        await callback.answer()
        await callback.message.edit_text("Введите процент чаевых (число):")
        await state.set_state(VotingStates.custom_tip)
        return

    await callback.answer()
    tip_percent = int(tip_value)
    await state.update_data(my_tip=tip_percent)

    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    await svc.set_member_tip(session_id, callback.from_user.id, tip_percent)

    text = await _build_summary_text(db, session_id, callback.from_user.id, tip_percent)
    await callback.message.edit_text(text, reply_markup=participant_summary_kb())


@router.message(VotingStates.custom_tip)
async def handle_custom_tip_input(message: Message, state: FSMContext, db: AsyncSession):
    try:
        tip_percent = int(message.text.strip().replace("%", ""))
    except ValueError:
        await message.answer("Введите число (например: 12).")
        return

    await state.update_data(my_tip=tip_percent)
    await state.set_state(None)

    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    await svc.set_member_tip(session_id, message.from_user.id, tip_percent)

    text = await _build_summary_text(db, session_id, message.from_user.id, tip_percent)
    await message.answer(text, reply_markup=participant_summary_kb())


# --- Summary actions ---

@router.callback_query(F.data == "pconfirm")
async def handle_participant_confirm(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer("Подтверждено!")
    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    await svc.confirm_member(session_id, callback.from_user.id)

    await callback.message.edit_text("✅ Ваш выбор подтверждён. Ожидайте итогов от админа.")

    # Notify admin
    session = await svc.get_session_by_id(session_id)
    member = await svc.get_member(session_id, callback.from_user.id)
    confirmed_count = sum(1 for m in session.members if m.confirmed)
    total_count = len(session.members)

    bot: Bot = callback.bot
    await bot.send_message(
        session.admin_tg_id,
        f"✅ {member.display_name} подтвердил(а) выбор ({confirmed_count}/{total_count})",
    )


@router.callback_query(F.data == "preselect")
async def handle_reselect_dishes(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    """Go back to dish selection."""
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]
    page = data.get("vote_page", 0)
    await _send_voting_keyboard(callback, db, session_id, callback.from_user.id, page)


@router.callback_query(F.data == "pretip")
async def handle_change_tip(callback: CallbackQuery, state: FSMContext):
    """Go back to tip selection."""
    await callback.answer()
    await callback.message.edit_text(
        "Выберите процент чаевых:",
        reply_markup=participant_tip_kb(),
    )


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
