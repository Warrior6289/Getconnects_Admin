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


def _get_table_name() -> str:
    """Determine the correct table name (may have been renamed by c1d8bd0c476f)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = {name.lower() for name in inspector.get_table_names(schema="public")}
    
    if "client_lead_type_settings" in tables:
        return "client_lead_type_settings"
    elif "client_dispositions" in tables:
        return "client_dispositions"
    else:
        raise RuntimeError("Neither client_dispositions nor client_lead_type_settings table found")


def upgrade() -> None:
    """Upgrade schema."""
    table_name = _get_table_name()
    
    op.add_column(
        table_name,
        sa.Column("sms_template", sa.Text(), nullable=True),
    )
    op.add_column(
        table_name,
        sa.Column("email_subject", sa.String(), nullable=True),
    )
    op.add_column(
        table_name,
        sa.Column("email_html", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    table_name = _get_table_name()
    
    op.drop_column(table_name, "email_html")
    op.drop_column(table_name, "email_subject")
    op.drop_column(table_name, "sms_template")
