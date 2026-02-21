"""i18n configuration. Uses aiogram built-in gettext, locale from User.language_code."""

from collections.abc import Callable

from aiogram.utils.i18n import I18n
from aiogram.utils.i18n.middleware import SimpleI18nMiddleware

i18n = I18n(
    path="locales",
    default_locale="ru",
    domain="messages",
)

i18n_middleware = SimpleI18nMiddleware(i18n)


def get_translator(locale: str | None = None) -> Callable[[str], str]:
    """Return gettext for locale. If None, use current (from middleware) or default."""
    if locale and locale in i18n.available_locales:
        loc = locale
    elif locale:
        loc = locale[:2] if locale[:2] in i18n.available_locales else i18n.default_locale
    else:
        loc = i18n.current_locale
    return lambda s: i18n.gettext(s, locale=loc)
