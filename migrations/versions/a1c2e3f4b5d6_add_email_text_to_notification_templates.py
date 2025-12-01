"""add email_text to notification templates"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1c2e3f4b5d6"
down_revision: Union[str, Sequence[str], None] = "04bc1b480b3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("notification_templates", sa.Column("email_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("notification_templates", "email_text")
