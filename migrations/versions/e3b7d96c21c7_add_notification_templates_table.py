"""add notification templates table and fk"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e3b7d96c21c7"
down_revision: Union[str, Sequence[str], None] = "dac4bf5b4961"
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
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("sms_template", sa.Text(), nullable=True),
        sa.Column("email_subject", sa.String(), nullable=True),
        sa.Column("email_html", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    
    table_name = _get_table_name()
    
    op.add_column(
        table_name,
        sa.Column("template_id", sa.Integer(), nullable=True),
    )
    
    # Use appropriate constraint name based on table name
    constraint_name = f"{table_name}_template_id_fkey"
    op.create_foreign_key(
        constraint_name,
        table_name,
        "notification_templates",
        ["template_id"],
        ["id"],
    )


def downgrade() -> None:
    table_name = _get_table_name()
    constraint_name = f"{table_name}_template_id_fkey"
    
    op.drop_constraint(
        constraint_name, table_name, type_="foreignkey"
    )
    op.drop_column(table_name, "template_id")
    op.drop_table("notification_templates")
