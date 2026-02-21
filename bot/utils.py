"""Utility functions."""

from decimal import Decimal

CURRENCY_SYMBOLS: dict[str, str] = {
    "RUB": "₽",
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "UAH": "₴",
    "KZT": "₸",
    "TRY": "₺",
    "PLN": "zł",
    "CHF": "Fr",
    "CNY": "¥",
    "JPY": "¥",
}


def format_price(amount: Decimal | int | float, currency: str = "RUB") -> str:
    """Format amount with currency symbol. E.g. 123.45, 'EUR' -> '123.45 €'."""
    code = (currency or "RUB").upper()[:8]
    symbol = CURRENCY_SYMBOLS.get(code, code)
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))
    if code == "JPY":
        return f"{int(amount)} {symbol}"
    return f"{amount:.2f} {symbol}"
