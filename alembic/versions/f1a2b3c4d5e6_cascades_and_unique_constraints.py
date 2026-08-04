"""add ON DELETE rules, unique constraints and FK indexes

Fixes two production-only failure modes that the SQLite test suite could not see
(SQLite skips FK enforcement unless PRAGMA foreign_keys=ON):

1. Deleting a session or an item raised IntegrityError because no FK carried an
   ON DELETE rule and no relationship carried a cascade. `DELETE /api/sessions/history`
   failed 100% of the time (the admin is always a member of their own session).
2. session_members and item_votes had no uniqueness guarantee, so a race (double-tapped
   deep link, double-tapped dish) inserted a duplicate row and every subsequent
   scalar_one_or_none() raised MultipleResultsFound for that user — permanently.

Duplicate rows are merged before the unique indexes go on: for members the earliest
row wins, for votes the quantities are summed and clamped to the item quantity.

Revision ID: f1a2b3c4d5e6
Revises: 5a1b2c3d4e5f
Create Date: 2026-08-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "5a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (constraint name, table, referred table, local col, ondelete)
_FKS = [
    ("session_photos_session_id_fkey", "session_photos", "sessions", "session_id", "CASCADE"),
    ("session_items_session_id_fkey", "session_items", "sessions", "session_id", "CASCADE"),
    ("session_members_session_id_fkey", "session_members", "sessions", "session_id", "CASCADE"),
    ("item_votes_item_id_fkey", "item_votes", "session_items", "item_id", "CASCADE"),
    ("payments_session_id_fkey", "payments", "sessions", "session_id", "SET NULL"),
]


def _dedupe() -> None:
    """Collapse duplicate members/votes/payments so the unique indexes can be created.

    Postgres-only, like every migration here. Duplicates are ranked by their natural
    timestamp with ``ctid`` as the tie-break — ``id`` is a uuid, and Postgres has no
    ordering aggregate for uuid, so MIN(id) is not available to pick a survivor.
    """
    conn = op.get_bind()

    # Members: keep the earliest join, drop the rest.
    conn.execute(
        sa.text(
            """
            DELETE FROM session_members AS a
            USING session_members AS b
            WHERE a.session_id = b.session_id
              AND a.user_tg_id = b.user_tg_id
              AND (a.joined_at, a.ctid) > (b.joined_at, b.ctid)
            """
        )
    )

    # Votes: fold the duplicates' quantities into every copy first (clamped to the
    # dish quantity, so a merge can never claim more units than exist), then drop all
    # but the earliest copy — which now carries the merged total.
    conn.execute(
        sa.text(
            """
            UPDATE item_votes AS v
            SET quantity = LEAST(agg.total, i.quantity)
            FROM (
                SELECT item_id, user_tg_id, SUM(quantity) AS total, COUNT(*) AS copies
                FROM item_votes
                GROUP BY item_id, user_tg_id
            ) AS agg
            JOIN session_items AS i ON i.id = agg.item_id
            WHERE v.item_id = agg.item_id
              AND v.user_tg_id = agg.user_tg_id
              AND agg.copies > 1
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM item_votes AS a
            USING item_votes AS b
            WHERE a.item_id = b.item_id
              AND a.user_tg_id = b.user_tg_id
              AND (a.created_at, a.ctid) > (b.created_at, b.ctid)
            """
        )
    )

    # Payments: a redelivered successful_payment recorded the same charge twice.
    conn.execute(
        sa.text(
            """
            DELETE FROM payments AS a
            USING payments AS b
            WHERE a.telegram_charge_id = b.telegram_charge_id
              AND (a.created_at, a.ctid) > (b.created_at, b.ctid)
            """
        )
    )


def upgrade() -> None:
    _dedupe()

    for name, table, referred, col, ondelete in _FKS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, referred, [col], ["id"], ondelete=ondelete)

    op.create_unique_constraint(
        "uq_session_members_session_user", "session_members", ["session_id", "user_tg_id"]
    )
    op.create_unique_constraint("uq_item_votes_item_user", "item_votes", ["item_id", "user_tg_id"])

    # Telegram redelivers successful_payment on retry; without this the same charge is
    # recorded twice and the paid scans are granted twice. (Duplicates already merged
    # in _dedupe above.)
    op.create_unique_constraint("uq_payments_charge_id", "payments", ["telegram_charge_id"])

    # FK columns were unindexed: every cascade delete and every membership lookup
    # was a sequential scan.
    op.create_index("ix_session_photos_session_id", "session_photos", ["session_id"])
    op.create_index("ix_session_items_session_id", "session_items", ["session_id"])
    op.create_index("ix_session_members_session_id", "session_members", ["session_id"])
    op.create_index("ix_session_members_user_tg_id", "session_members", ["user_tg_id"])
    op.create_index("ix_item_votes_item_id", "item_votes", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_item_votes_item_id", "item_votes")
    op.drop_index("ix_session_members_user_tg_id", "session_members")
    op.drop_index("ix_session_members_session_id", "session_members")
    op.drop_index("ix_session_items_session_id", "session_items")
    op.drop_index("ix_session_photos_session_id", "session_photos")

    op.drop_constraint("uq_payments_charge_id", "payments", type_="unique")
    op.drop_constraint("uq_item_votes_item_user", "item_votes", type_="unique")
    op.drop_constraint("uq_session_members_session_user", "session_members", type_="unique")

    for name, table, referred, col, _ondelete in _FKS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, referred, [col], ["id"])
