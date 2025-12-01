"""add justcall webhook table

Revision ID: 81d1c3a74f3e
Revises: 7cb5a503b498
Create Date: 2025-08-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '81d1c3a74f3e'
down_revision: Union[str, Sequence[str], None] = '7cb5a503b498'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'justcall_webhooks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('justcall_webhooks')
