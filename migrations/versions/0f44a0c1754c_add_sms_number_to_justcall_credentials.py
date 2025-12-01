"""add sms_number to justcall credentials"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0f44a0c1754c'
down_revision: Union[str, Sequence[str], None] = 'e6c7c96d6e7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('justcall_credentials', sa.Column('sms_number', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('justcall_credentials', 'sms_number')
