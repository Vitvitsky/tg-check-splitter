"""add currency to sessions

Revision ID: 5a1b2c3d4e5f
Revises: 4eb5c3f19b63
Create Date: 2026-02-16 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5a1b2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = '4eb5c3f19b63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sessions', sa.Column('currency', sa.String(8), server_default='RUB', nullable=False))


def downgrade() -> None:
    op.drop_column('sessions', 'currency')
