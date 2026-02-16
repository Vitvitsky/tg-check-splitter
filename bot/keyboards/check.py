from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

MAIN_MENU_BTN = "📸 Разделить чек"


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=MAIN_MENU_BTN)]],
        resize_keyboard=True,
        persistent=True,
    )


def photo_collected_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Распознать", callback_data="ocr_start")],
    ])


def ocr_result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Всё верно", callback_data="ocr_confirm"),
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="ocr_edit"),
        ],
        [InlineKeyboardButton(text="🔄 Переотправить", callback_data="ocr_retry")],
    ])
