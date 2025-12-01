"""add notes column to leads"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '91b49bf0e677'
down_revision: Union[str, Sequence[str], None] = '0f44a0c1754c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('leads', sa.Column('notes', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('leads', 'notes')
