"""add payload log and mapping"""

from alembic import op
import sqlalchemy as sa

revision = 'e6c7c96d6e7b'
down_revision = '81d1c3a74f3e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('justcall_webhooks', sa.Column('mapping', sa.JSON(), nullable=True))
    op.create_table(
        'justcall_webhook_payloads',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('token_id', sa.Integer(), sa.ForeignKey('justcall_webhooks.id'), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_justcall_webhook_payloads_token_id', 'justcall_webhook_payloads', ['token_id'])


def downgrade():
    op.drop_index('ix_justcall_webhook_payloads_token_id', table_name='justcall_webhook_payloads')
    op.drop_table('justcall_webhook_payloads')
    op.drop_column('justcall_webhooks', 'mapping')
