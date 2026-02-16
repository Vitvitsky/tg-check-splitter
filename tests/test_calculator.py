from decimal import Decimal

from bot.services.calculator import calculate_shares


def test_simple_split():
    """Each person took one unique dish."""
    items = [
        {"price": Decimal("650"), "votes": [111]},
        {"price": Decimal("450"), "votes": [222]},
    ]
    result = calculate_shares(items, tip_percent=0)
    assert result == {111: Decimal("650"), 222: Decimal("450")}


def test_shared_dish():
    """Two people share one dish."""
    items = [
        {"price": Decimal("650"), "votes": [111, 222]},
    ]
    result = calculate_shares(items, tip_percent=0)
    assert result == {111: Decimal("325"), 222: Decimal("325")}


def test_with_tips():
    """10% tips applied."""
    items = [
        {"price": Decimal("1000"), "votes": [111]},
    ]
    result = calculate_shares(items, tip_percent=10)
    assert result == {111: Decimal("1100")}


def test_rounding_up():
    """Shares round up to whole unit."""
    items = [
        {"price": Decimal("100"), "votes": [111, 222, 333]},
    ]
    result = calculate_shares(items, tip_percent=0)
    # 100 / 3 = 33.33... → ceil to 34 each
    assert result[111] == Decimal("34")
    assert result[222] == Decimal("34")
    assert result[333] == Decimal("34")


def test_multiple_items_per_person():
    """One person votes for multiple items."""
    items = [
        {"price": Decimal("650"), "votes": [111, 222]},
        {"price": Decimal("450"), "votes": [222]},
    ]
    result = calculate_shares(items, tip_percent=10)
    # 111: 325 * 1.1 = 357.5 → 358
    # 222: (325 + 450) * 1.1 = 852.5 → 853
    assert result == {111: Decimal("358"), 222: Decimal("853")}


def test_no_votes_item_ignored():
    """Items with no votes don't affect calculation."""
    items = [
        {"price": Decimal("500"), "votes": [111]},
        {"price": Decimal("300"), "votes": []},
    ]
    result = calculate_shares(items, tip_percent=0)
    assert result == {111: Decimal("500")}


def test_empty_items():
    """No items returns empty dict."""
    result = calculate_shares([], tip_percent=0)
    assert result == {}
