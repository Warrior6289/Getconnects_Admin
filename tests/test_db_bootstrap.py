"""Tests for database bootstrap helpers."""

from sqlalchemy import create_engine, inspect, text

from getconnects_admin.db_bootstrap import ensure_lead_type_tables


def _table_set(engine):
    inspector = inspect(engine)
    return {name.lower() for name in inspector.get_table_names()}


def test_ensure_lead_type_tables_renames_sqlite():
    """Renaming legacy tables works on SQLite deployments."""

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE dispositions (id TEXT PRIMARY KEY, name TEXT, group_id TEXT)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE client_dispositions (id TEXT PRIMARY KEY, name TEXT)"
            )
        )

    ensure_lead_type_tables(engine)

    tables = _table_set(engine)
    assert "lead_types" in tables
    assert "client_lead_type_settings" in tables
    assert "dispositions" not in tables
    assert "client_dispositions" not in tables


def test_ensure_lead_type_tables_is_idempotent():
    """Running the helper multiple times keeps the schema stable."""

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE dispositions (id TEXT PRIMARY KEY, name TEXT, group_id TEXT)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE client_dispositions (id TEXT PRIMARY KEY, name TEXT)"
            )
        )

    ensure_lead_type_tables(engine)
    ensure_lead_type_tables(engine)

    tables = _table_set(engine)
    assert tables == {"lead_types", "client_lead_type_settings"}
