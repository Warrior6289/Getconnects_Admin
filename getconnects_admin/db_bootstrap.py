"""Database bootstrap helpers for legacy deployments."""

from __future__ import annotations

from contextlib import suppress

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _schema_for(engine: Engine) -> str | None:
    """Return the default schema for the engine if applicable."""

    if engine.dialect.name == "postgresql":
        return "public"
    return None


def _table_names(engine: Engine, schema: str | None) -> set[str]:
    """Return a case-insensitive set of table names for *schema*."""

    inspector = inspect(engine)
    return {name.lower() for name in inspector.get_table_names(schema=schema)}


def _policy_exists(engine: Engine, table: str, policy: str) -> bool:
    """Check if the named PostgreSQL policy exists."""

    if engine.dialect.name != "postgresql":  # pragma: no cover - depends on PG
        return False

    with engine.connect() as conn:
        result = conn.execute(
            text(
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


def _qualified(schema: str | None, identifier: str) -> str:
    """Return an optionally schema-qualified identifier."""

    if schema:
        return f"{schema}.{identifier}"
    return identifier


def ensure_lead_type_tables(engine: Engine) -> None:
    """Ensure legacy disposition tables are renamed to lead type tables.

    Older deployments used the table names ``dispositions`` and
    ``client_dispositions``. The ORM now expects ``lead_types`` and
    ``client_lead_type_settings`` respectively. Render environments may not run
    Alembic migrations automatically, so we perform a lightweight, idempotent
    migration here to avoid runtime errors when the tables have not been
    renamed yet.
    """

    if engine is None:
        return

    schema = _schema_for(engine)

    # Refresh table names inside the transaction so we see the latest state.
    def current_tables() -> set[str]:
        return _table_names(engine, schema)

    tables = current_tables()

    if "client_lead_type_settings" not in tables and "client_dispositions" in tables:
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"ALTER TABLE {_qualified(schema, 'client_dispositions')} "
                    "RENAME TO client_lead_type_settings"
                )
            )
        if _policy_exists(engine, "client_lead_type_settings", "client_dispositions_all_access"):
            with suppress(Exception):  # pragma: no cover - depends on PG policies
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "ALTER POLICY \"client_dispositions_all_access\" "
                            f"ON {_qualified(schema, 'client_lead_type_settings')} "
                            "RENAME TO \"client_lead_type_settings_all_access\""
                        )
                    )

        tables = current_tables()

    if "lead_types" not in tables and "dispositions" in tables:
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"ALTER TABLE {_qualified(schema, 'dispositions')} "
                    "RENAME TO lead_types"
                )
            )
        if _policy_exists(engine, "lead_types", "dispositions_all_access"):
            with suppress(Exception):  # pragma: no cover - depends on PG policies
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "ALTER POLICY \"dispositions_all_access\" "
                            f"ON {_qualified(schema, 'lead_types')} "
                            "RENAME TO \"lead_types_all_access\""
                        )
                    )
