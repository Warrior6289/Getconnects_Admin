import importlib
import getconnects_admin.models as models


def test_postgres_scheme_normalised(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost/db")
    importlib.reload(models)
    assert models.DATABASE_URL == "postgresql://user:pass@localhost/db"
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    importlib.reload(models)
