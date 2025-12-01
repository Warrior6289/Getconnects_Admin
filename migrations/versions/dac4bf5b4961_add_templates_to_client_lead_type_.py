"""add templates to client lead type settings

Revision ID: dac4bf5b4961
Revises: 1d16f9446cd3
Create Date: 2025-08-21 13:10:41.278709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dac4bf5b4961'
down_revision: Union[str, Sequence[str], None] = '1d16f9446cd3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "client_dispositions",
        sa.Column("sms_template", sa.Text(), nullable=True),
    )
    op.add_column(
        "client_dispositions",
        sa.Column("email_subject", sa.String(), nullable=True),
    )
    op.add_column(
        "client_dispositions",
        sa.Column("email_html", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("client_dispositions", "email_html")
    op.drop_column("client_dispositions", "email_subject")
    op.drop_column("client_dispositions", "sms_template")
