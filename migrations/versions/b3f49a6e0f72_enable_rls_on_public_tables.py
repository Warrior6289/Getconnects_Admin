"""enable rls on public tables"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b3f49a6e0f72"
down_revision: Union[str, Sequence[str], None] = "04bc1b480b3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    "alembic_version",
    "justcall_credentials",
    "clients",
    "campaigns",
    "disposition_groups",
    "dispositions",
    "users",
    "page_permissions",
    "campaign_disposition_groups",
    "campaign_dispositions",
    "client_dispositions",
    "notification_logs",
    "leads",
    "notification_templates",
    "justcall_webhooks",
    "justcall_webhook_payloads",
    "gmail_credentials",
]


def upgrade() -> None:
    for table in TABLES:
        op.execute(
            f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;"
        )
        op.execute(
            f'CREATE POLICY "{table}_all_access" ON public.{table} '
            f"FOR ALL USING (true) WITH CHECK (true);"
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(
            f'DROP POLICY IF EXISTS "{table}_all_access" ON public.{table};'
        )
        op.execute(
            f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;"
        )
