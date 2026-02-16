from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def items_page_kb(
    items: list[dict],
    user_votes: dict[UUID, int],
    page: int = 0,
    page_size: int = 8,
) -> InlineKeyboardMarkup:
    """Build voting keyboard.

    items: [{"id", "name", "price", "quantity", "total_claimed"}]
    user_votes: {item_id: user_claimed_qty}
    """
    start = page * page_size
    end = start + page_size
    page_items = items[start:end]

    buttons = []
    for item in page_items:
        my_qty = user_votes.get(item["id"], 0)
        max_qty = item["quantity"]
        total_claimed = item["total_claimed"]

        if max_qty > 1:
            if my_qty > 0:
                prefix = f"[{my_qty}/{max_qty}]"
            else:
                prefix = "◻️"
            label = f"{prefix} {item['name']} — {item['price']}₽ (×{max_qty})"
        else:
            prefix = "☑️" if my_qty else "◻️"
            label = f"{prefix} {item['name']} — {item['price']}₽"

        if total_claimed > 0:
            label += f" 👤{total_claimed}"

        buttons.append(
            [InlineKeyboardButton(text=label, callback_data=f"vote:{item['id']}")]
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="← Назад", callback_data=f"page:{page - 1}"))
    if end < len(items):
        nav.append(InlineKeyboardButton(text="Далее →", callback_data=f"page:{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append(
        [InlineKeyboardButton(text="✅ Готово", callback_data="vote_done")]
    )
    buttons.append(
        [InlineKeyboardButton(text="⚠️ Не вижу своё блюдо", callback_data="missing_item")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def participant_tip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="0%", callback_data="ptip:0"),
            InlineKeyboardButton(text="5%", callback_data="ptip:5"),
            InlineKeyboardButton(text="10%", callback_data="ptip:10"),
            InlineKeyboardButton(text="15%", callback_data="ptip:15"),
        ],
        [InlineKeyboardButton(text="Другой %", callback_data="ptip:custom")],
        [InlineKeyboardButton(text="← Перевыбрать блюда", callback_data="ptip:back")],
    ])


def participant_summary_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="pconfirm")],
        [InlineKeyboardButton(text="← Перевыбрать блюда", callback_data="preselect")],
        [InlineKeyboardButton(text="✏️ Изменить чаевые", callback_data="pretip")],
    ])
