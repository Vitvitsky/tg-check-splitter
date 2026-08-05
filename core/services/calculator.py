import math
from decimal import Decimal


def calculate_shares(
    items: list[dict],
    tip_percent: int = 0,
    per_person_tips: dict[int, int] | None = None,
) -> dict[int, Decimal]:
    """Calculate each user's share from voted items.

    Args:
        items: [{"price": Decimal, "quantity": int, "votes": {user_tg_id: claimed_qty}}]
        tip_percent: global tip percentage (fallback, 0-100)
        per_person_tips: {user_tg_id: tip_percent} — individual tips override global

    Returns:
        {user_tg_id: total_amount} with amounts rounded up to whole units.
    """
    raw_shares: dict[int, Decimal] = {}

    for item in items:
        votes = item["votes"]
        if not votes:
            continue
        qty = item.get("quantity", 1)
        per_unit = item["price"] / Decimal(qty) if qty else item["price"]

        if isinstance(votes, dict):
            # New format: {user_tg_id: claimed_qty}
            for user_id, claimed in votes.items():
                raw_shares[user_id] = raw_shares.get(user_id, Decimal("0")) + per_unit * claimed
        else:
            # Legacy format: [user_tg_id, ...]
            per_person = item["price"] / len(votes)
            for user_id in votes:
                raw_shares[user_id] = raw_shares.get(user_id, Decimal("0")) + per_person

    result = {}
    for user_id, share in raw_shares.items():
        tip = per_person_tips.get(user_id, tip_percent) if per_person_tips else tip_percent
        tip_multiplier = Decimal(1) + Decimal(tip) / Decimal(100)
        result[user_id] = Decimal(math.ceil(share * tip_multiplier))

    return result


def calculate_user_share(
    items: list[dict],
    user_tg_id: int,
    tip_percent: int = 0,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calculate a single user's share breakdown.

    Returns:
        (dishes_total, tip_amount, grand_total)
    """
    dishes_total = Decimal("0")
    for item in items:
        votes = item["votes"]
        if not votes:
            continue
        qty = item.get("quantity", 1)
        per_unit = item["price"] / Decimal(qty) if qty else item["price"]

        if isinstance(votes, dict):
            claimed = votes.get(user_tg_id, 0)
            if claimed:
                dishes_total += per_unit * claimed
        else:
            if user_tg_id in votes:
                dishes_total += item["price"] / len(votes)

    tip_amount = dishes_total * Decimal(tip_percent) / Decimal(100)
    grand_total = Decimal(math.ceil(dishes_total + tip_amount))
    return dishes_total, tip_amount, grand_total
