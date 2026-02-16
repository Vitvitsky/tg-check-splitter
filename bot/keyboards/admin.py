from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def voting_progress_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Текущий расчёт", callback_data="admin_preview"),
            InlineKeyboardButton(text="⏹ Завершить", callback_data="admin_finish"),
        ],
    ])


def unvoted_items_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Вернуть голосование", callback_data="admin_reopen")],
        [InlineKeyboardButton(text="➗ Разделить поровну", callback_data="admin_split_equal")],
        [InlineKeyboardButton(text="🗑 Убрать из счёта", callback_data="admin_remove_unvoted")],
    ])


def tip_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="0%", callback_data="tip:0"),
            InlineKeyboardButton(text="5%", callback_data="tip:5"),
            InlineKeyboardButton(text="10%", callback_data="tip:10"),
            InlineKeyboardButton(text="15%", callback_data="tip:15"),
        ],
        [InlineKeyboardButton(text="Другой %", callback_data="tip:custom")],
    ])


def settle_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Все рассчитались", callback_data="admin_settle")],
    ])
