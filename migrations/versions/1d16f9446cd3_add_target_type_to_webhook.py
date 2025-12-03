"""add target_type to justcall webhooks"""

from alembic import op
import sqlalchemy as sa

revision = '1d16f9446cd3'
down_revision = 'e6c7c96d6e7b'
branch_labels = None
depends_on = None


def upgrade():
    # Add column with server_default
    op.add_column(
        "justcall_webhooks",
        sa.Column("target_type", sa.String(), nullable=False, server_default="lead"),
    )
    
    # Remove server_default using direct SQL to avoid table recreation
    # This avoids the foreign key dependency issue
    op.execute("ALTER TABLE justcall_webhooks ALTER COLUMN target_type DROP DEFAULT")


def downgrade():
    op.drop_column('justcall_webhooks', 'target_type')
