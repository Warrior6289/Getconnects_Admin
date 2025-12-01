"""add target_type to justcall webhooks"""

from alembic import op
import sqlalchemy as sa

revision = '1d16f9446cd3'
down_revision = 'e6c7c96d6e7b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "justcall_webhooks",
        sa.Column("target_type", sa.String(), nullable=False, server_default="lead"),
    )
    with op.batch_alter_table("justcall_webhooks", recreate="always") as batch_op:
        batch_op.alter_column(
            "target_type",
            existing_type=sa.String(),
            server_default=None,
            existing_server_default=sa.text("'lead'"),
        )


def downgrade():
    op.drop_column('justcall_webhooks', 'target_type')
