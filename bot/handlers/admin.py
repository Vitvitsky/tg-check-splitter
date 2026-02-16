import io

import qrcode
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.voting import send_voting_keyboard_to_user
from bot.keyboards.admin import settle_kb, unvoted_items_kb, voting_progress_kb
from bot.services.calculator import calculate_shares
from bot.services.session import SessionService

router = Router()


@router.callback_query(F.data == "ocr_confirm")
async def confirm_ocr(callback: CallbackQuery, state: FSMContext, db: AsyncSession, bot: Bot):
    """Admin confirms OCR results -> generate QR + invite link + notify participants."""
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)

    await svc.update_status(session_id, "voting")

    bot_info = await bot.get_me()
    invite_url = f"https://t.me/{bot_info.username}?start={session.invite_code}"

    qr = qrcode.make(invite_url)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)

    await callback.message.answer_photo(
        BufferedInputFile(buf.read(), filename="qr.png"),
        caption=(
            f"Ссылка для участников:\n{invite_url}\n\n"
            "Покажите QR-код или отправьте ссылку участникам."
        ),
    )
    await callback.message.answer(
        "Ожидаю участников...",
        reply_markup=voting_progress_kb(),
    )

    # Send voting keyboard to admin and all already-joined participants
    for member in session.members:
        await send_voting_keyboard_to_user(bot, db, member.user_tg_id, session_id)


@router.callback_query(F.data == "admin_preview")
async def preview_results(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]
    text = await _format_results(db, session_id)
    await callback.message.answer(f"Предварительный расчёт:\n\n{text}")


@router.callback_query(F.data == "admin_finish")
async def finish_voting(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]
    svc = SessionService(db)
    unvoted = await svc.get_unvoted_items(session_id)

    if unvoted:
        lines = ["Никто не отметил:"]
        for item in unvoted:
            lines.append(f"- {item.name} -- {item.price}₽")
        await callback.message.edit_text("\n".join(lines), reply_markup=unvoted_items_kb())
    else:
        text = await _format_results(db, session_id)
        await callback.message.edit_text(
            f"Итоги сессии:\n\n{text}",
            reply_markup=settle_kb(),
        )


@router.callback_query(F.data == "admin_reopen")
async def reopen_voting(callback: CallbackQuery):
    await callback.answer("Голосование продолжается.")
    await callback.message.edit_text("Голосование открыто.", reply_markup=voting_progress_kb())


@router.callback_query(F.data == "admin_split_equal")
async def split_unvoted_equal(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    unvoted = await svc.get_unvoted_items(session_id)

    n_members = len(session.members)
    for item in unvoted:
        remaining = item.quantity - sum(v.quantity for v in item.votes)
        if remaining <= 0:
            continue
        # Distribute remaining equally (at least 1 per member, round-robin if needed)
        base_qty = max(remaining // n_members, 1) if n_members else remaining
        for member in session.members:
            if remaining <= 0:
                break
            qty = min(base_qty, remaining)
            await svc.add_vote_all(item.id, member.user_tg_id, qty)
            remaining -= qty

    text = await _format_results(db, session_id)
    await callback.message.edit_text(
        f"Итоги сессии:\n\n{text}",
        reply_markup=settle_kb(),
    )


@router.callback_query(F.data == "admin_remove_unvoted")
async def remove_unvoted(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]
    svc = SessionService(db)
    await svc.delete_unvoted_items(session_id)
    text = await _format_results(db, session_id)
    await callback.message.edit_text(
        f"Итоги сессии:\n\n{text}",
        reply_markup=settle_kb(),
    )


@router.callback_query(F.data == "admin_settle")
async def settle_session(callback: CallbackQuery, state: FSMContext, db: AsyncSession, bot: Bot):
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    await svc.update_status(session_id, "closed")
    session = await svc.get_session_by_id(session_id)
    text = await _format_results(db, session_id)

    # Notify all members with per-person tips
    items_data = [
        {"price": item.price, "quantity": item.quantity, "votes": {v.user_tg_id: v.quantity for v in item.votes}}
        for item in session.items
    ]
    per_person_tips = {
        m.user_tg_id: (m.tip_percent if m.tip_percent is not None else 0)
        for m in session.members
    }
    shares = calculate_shares(items_data, per_person_tips=per_person_tips)

    for member in session.members:
        share = int(shares.get(member.user_tg_id, 0))
        tip = member.tip_percent if member.tip_percent is not None else 0
        await bot.send_message(
            member.user_tg_id,
            f"Сессия завершена!\nТвоя доля: {share}₽ (чаевые {tip}%)",
        )

    await callback.message.edit_text(f"Сессия закрыта!\n\n{text}")
    await state.clear()


async def _format_results(db: AsyncSession, session_id: str) -> str:
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)

    items_data = [
        {"price": item.price, "quantity": item.quantity, "votes": {v.user_tg_id: v.quantity for v in item.votes}}
        for item in session.items
    ]

    per_person_tips = {
        m.user_tg_id: (m.tip_percent if m.tip_percent is not None else 0)
        for m in session.members
    }
    shares = calculate_shares(items_data, per_person_tips=per_person_tips)

    members_map = {m.user_tg_id: m for m in session.members}

    lines = []
    total = sum(shares.values())
    for user_id, amount in sorted(shares.items(), key=lambda x: -x[1]):
        member = members_map.get(user_id)
        name = member.display_name if member else f"User {user_id}"
        tip = member.tip_percent if member and member.tip_percent is not None else 0
        confirmed = "✅" if member and member.confirmed else "⏳"
        lines.append(f"{confirmed} {name} — {int(amount)}₽ (чаевые {tip}%)")

    raw_total = sum(i.price for i in session.items)
    tip_total = total - raw_total

    lines.append("─" * 25)
    lines.append(f"Блюда: {int(raw_total)}₽")
    if tip_total:
        lines.append(f"Чаевые: {int(tip_total)}₽")
    lines.append(f"Всего: {int(total)}₽")

    not_confirmed = [m for m in session.members if not m.confirmed]
    if not_confirmed:
        names = ", ".join(m.display_name for m in not_confirmed)
        lines.append(f"\n⏳ Не подтвердили: {names}")

    return "\n".join(lines)
