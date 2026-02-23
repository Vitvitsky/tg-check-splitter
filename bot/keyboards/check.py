from collections.abc import Callable

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)


def main_menu_kb(t: Callable[[str], str]) -> ReplyKeyboardMarkup:
    """t is gettext function _ from handler context."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("Split check"))],
            [KeyboardButton(text=t("My quota")), KeyboardButton(text=t("Help"))],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def photo_collected_kb(t: Callable[[str], str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("Recognize"), callback_data="ocr_start")],
        ]
    )


def webapp_button_kb(url: str, text: str = "Открыть Mini App") -> InlineKeyboardMarkup:
    """Create an inline keyboard with a single WebAppInfo button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))],
        ]
    )


def ocr_result_kb(t: Callable[[str], str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("All correct"), callback_data="ocr_confirm"),
                InlineKeyboardButton(text=t("Edit"), callback_data="ocr_edit"),
            ],
            [InlineKeyboardButton(text=t("Resend"), callback_data="ocr_retry")],
        ]
    )
