import math
from decimal import Decimal


def calculate_shares(
    items: list[dict],
    tip_percent: int,
) -> dict[int, Decimal]:
    """Calculate each user's share from voted items.

    Args:
        items: [{"price": Decimal, "votes": [user_tg_id, ...]}]
        tip_percent: tip percentage (0-100)

    Returns:
        {user_tg_id: total_amount} with amounts rounded up to whole units.
    """
    raw_shares: dict[int, Decimal] = {}

    for item in items:
        voters = item["votes"]
        if not voters:
            continue
        per_person = item["price"] / len(voters)
        for user_id in voters:
            raw_shares[user_id] = raw_shares.get(user_id, Decimal("0")) + per_person

    tip_multiplier = Decimal(1) + Decimal(tip_percent) / Decimal(100)

    return {
        user_id: Decimal(math.ceil(share * tip_multiplier))
        for user_id, share in raw_shares.items()
    }
