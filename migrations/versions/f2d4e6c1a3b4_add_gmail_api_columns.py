"""add Gmail API credential columns

Revision ID: f2d4e6c1a3b4
Revises: 91b49bf0e677
Create Date: 2024-06-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f2d4e6c1a3b4"
down_revision = "91b49bf0e677"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "gmail_credentials",
        sa.Column("api_client_id", sa.String(), nullable=True),
    )
    op.add_column(
        "gmail_credentials",
        sa.Column("api_client_secret", sa.String(), nullable=True),
    )
    op.add_column(
        "gmail_credentials",
        sa.Column("api_refresh_token", sa.String(), nullable=True),
    )
    op.add_column(
        "gmail_credentials",
        sa.Column("api_from_email", sa.String(), nullable=True),
    )


def downgrade():
    op.drop_column("gmail_credentials", "api_from_email")
    op.drop_column("gmail_credentials", "api_refresh_token")
    op.drop_column("gmail_credentials", "api_client_secret")
    op.drop_column("gmail_credentials", "api_client_id")

