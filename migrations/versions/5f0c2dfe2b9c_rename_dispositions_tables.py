"""Rename dispositions tables to lead types"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "5f0c2dfe2b9c"
down_revision: Union[str, Sequence[str], None] = ("a1c2e3f4b5d6", "b3f49a6e0f72")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("dispositions", "lead_types")
    op.rename_table("client_dispositions", "client_lead_type_settings")

    op.execute(
        'ALTER POLICY "dispositions_all_access" ON public.lead_types '
        'RENAME TO "lead_types_all_access";'
    )
    op.execute(
        'ALTER POLICY "client_dispositions_all_access" '
        "ON public.client_lead_type_settings "
        'RENAME TO "client_lead_type_settings_all_access";'
    )


def downgrade() -> None:
    op.execute(
        'ALTER POLICY "client_lead_type_settings_all_access" '
        "ON public.client_lead_type_settings "
        'RENAME TO "client_dispositions_all_access";'
    )
    op.execute(
        'ALTER POLICY "lead_types_all_access" ON public.lead_types '
        'RENAME TO "dispositions_all_access";'
    )

    op.rename_table("client_lead_type_settings", "client_dispositions")
    op.rename_table("lead_types", "dispositions")
