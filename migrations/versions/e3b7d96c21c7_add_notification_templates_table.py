"""add notification templates table and fk"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e3b7d96c21c7"
down_revision: Union[str, Sequence[str], None] = "dac4bf5b4961"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    op.add_column(
        "client_dispositions",
        sa.Column("template_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "client_dispositions_template_id_fkey",
        "client_dispositions",
        "notification_templates",
        ["template_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "client_dispositions_template_id_fkey", "client_dispositions", type_="foreignkey"
    )
    op.drop_column("client_dispositions", "template_id")
    op.drop_table("notification_templates")
