"""Merge heads

Revision ID: 04bc1b480b3e
Revises: e3b7d96c21c7, 91b49bf0e677
Create Date: 2025-08-25 02:05:53.138942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04bc1b480b3e'
down_revision: Union[str, Sequence[str], None] = ('e3b7d96c21c7', '91b49bf0e677')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
