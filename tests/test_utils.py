from decimal import Decimal

from bot.utils import format_price


def test_format_price_rub():
    assert format_price(100, "RUB") == "100.00 ₽"
    assert format_price(Decimal("123.45"), "RUB") == "123.45 ₽"


def test_format_price_eur():
    assert format_price(50.5, "EUR") == "50.50 €"


def test_format_price_usd():
    assert format_price(99, "USD") == "99.00 $"


def test_format_price_jpy():
    assert format_price(1000, "JPY") == "1000 ¥"
    assert format_price(Decimal("1500.99"), "JPY") == "1500 ¥"


def test_format_price_unknown():
    assert format_price(100, "PLN") == "100.00 zł"
    assert format_price(100, "XYZ") == "100.00 XYZ"
