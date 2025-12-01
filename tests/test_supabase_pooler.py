import importlib
import pytest

import getconnects_admin.models as models


def test_pooler_requires_project_option(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:pass@db.supabase.co:6543/postgres",
    )
    with pytest.raises(RuntimeError, match="options=project"):
        importlib.reload(models)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    importlib.reload(models)


def test_pooler_accepts_project_option(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:pass@db.supabase.co:6543/postgres?options=project=myproj",
    )
    importlib.reload(models)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    importlib.reload(models)
