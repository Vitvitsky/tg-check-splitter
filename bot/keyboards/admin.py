from collections.abc import Callable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def voting_progress_kb(t: Callable[[str], str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("Current calculation"), callback_data="admin_preview"),
            InlineKeyboardButton(text=t("Finish"), callback_data="admin_finish"),
        ],
    ])


def unvoted_items_kb(t: Callable[[str], str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("Reopen voting"), callback_data="admin_reopen")],
        [InlineKeyboardButton(text=t("Split equal"), callback_data="admin_split_equal")],
        [InlineKeyboardButton(text=t("Remove from bill"), callback_data="admin_remove_unvoted")],
    ])


def tip_select_kb(t: Callable[[str], str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="0%", callback_data="tip:0"),
            InlineKeyboardButton(text="5%", callback_data="tip:5"),
            InlineKeyboardButton(text="10%", callback_data="tip:10"),
            InlineKeyboardButton(text="15%", callback_data="tip:15"),
        ],
        [InlineKeyboardButton(text=t("Other percent"), callback_data="tip:custom")],
    ])


def settle_kb(t: Callable[[str], str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("All settled"), callback_data="admin_settle")],
    ])
