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


def webapp_button_kb(url: str, text: str = "Открыть Mini App") -> InlineKeyboardMarkup:
    """Create an inline keyboard with a single WebAppInfo button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))],
        ]
    )
