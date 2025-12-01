"""ensure lead type tables exist"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c1d8bd0c476f"
down_revision = "e6c7c96d6e7b"
branch_labels = None
depends_on = None


def _table_names(inspector) -> set[str]:
    """Return a case-insensitive set of table names in the public schema."""

    return {name.lower() for name in inspector.get_table_names(schema="public")}


def _policy_exists(bind, table: str, policy: str) -> bool:
    """Check if a policy exists for the given table."""

    result = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_policies
            WHERE schemaname = :schema
              AND tablename = :table
              AND policyname = :policy
            """
        ),
        {"schema": "public", "table": table, "policy": policy},
    )
    return result.first() is not None


def upgrade() -> None:
    """Ensure legacy disposition tables are renamed to lead types."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = _table_names(inspector)

    if "client_lead_type_settings" not in tables and "client_dispositions" in tables:
        op.execute(
            "ALTER TABLE public.client_dispositions "
            "RENAME TO client_lead_type_settings"
        )
        if _policy_exists(
            bind, "client_lead_type_settings", "client_dispositions_all_access"
        ):
            op.execute(
                "ALTER POLICY \"client_dispositions_all_access\" "
                "ON public.client_lead_type_settings "
                "RENAME TO \"client_lead_type_settings_all_access\""
            )

    # Refresh table list after potential rename
    inspector = sa.inspect(bind)
    tables = _table_names(inspector)

    if "lead_types" not in tables and "dispositions" in tables:
        op.execute(
            "ALTER TABLE public.dispositions " "RENAME TO lead_types"
        )
        if _policy_exists(bind, "lead_types", "dispositions_all_access"):
            op.execute(
                "ALTER POLICY \"dispositions_all_access\" "
                "ON public.lead_types "
                "RENAME TO \"lead_types_all_access\""
            )


def downgrade() -> None:
    """Revert lead type table names to their legacy disposition names."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = _table_names(inspector)

    if "dispositions" not in tables and "lead_types" in tables:
        if _policy_exists(bind, "lead_types", "lead_types_all_access"):
            op.execute(
                "ALTER POLICY \"lead_types_all_access\" "
                "ON public.lead_types "
                "RENAME TO \"dispositions_all_access\""
            )
        op.execute(
            "ALTER TABLE public.lead_types " "RENAME TO dispositions"
        )

    inspector = sa.inspect(bind)
    tables = _table_names(inspector)

    if "client_dispositions" not in tables and "client_lead_type_settings" in tables:
        if _policy_exists(
            bind, "client_lead_type_settings", "client_lead_type_settings_all_access"
        ):
            op.execute(
                "ALTER POLICY \"client_lead_type_settings_all_access\" "
                "ON public.client_lead_type_settings "
                "RENAME TO \"client_dispositions_all_access\""
            )
        op.execute(
            "ALTER TABLE public.client_lead_type_settings "
            "RENAME TO client_dispositions"
        )
