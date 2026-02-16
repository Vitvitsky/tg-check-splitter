from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def items_page_kb(
    items: list[dict],
    user_votes: set[UUID],
    page: int = 0,
    page_size: int = 8,
) -> InlineKeyboardMarkup:
    start = page * page_size
    end = start + page_size
    page_items = items[start:end]

    buttons = []
    for item in page_items:
        voted = "☑️" if item["id"] in user_votes else "◻️"
        voter_count = item["voter_count"]
        label = f"{voted} {item['name']} — {item['price']}₽"
        if voter_count > 0:
            label += f" ({voter_count})"
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
