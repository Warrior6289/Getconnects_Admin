import os
import sys
import importlib
from pathlib import Path
import pytest
from cryptography.fernet import Fernet

os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("FLASK_SECRET_KEY", "testing-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root.parent))

import getconnects_admin
sys.modules.setdefault("models", getconnects_admin.models)
# Expose model submodules under the short ``models`` alias used in tests
for mod in [
    "user",
    "page_permission",
    "client",
    "campaign",
    "lead",
    "lead_type_group",
    "lead_type",
    "campaign_lead_type",
    "campaign_lead_type_group",
    "client_lead_type_setting",
    "notification_template",
    "notification_log",
    "justcall_credential",
    "justcall_webhook",
    "justcall_webhook_payload",
    "gmail_credential",
]:
    sys.modules.setdefault(f"models.{mod}", getattr(getconnects_admin.models, mod))
sys.modules.setdefault("services", getconnects_admin.services)
for mod in [
    "auth_service",
    "justcall_service",
    "client_service",
    "helpers",
    "lead_service",
    "campaign_service",
    "stats_service",
    "auth_decorators",
    "email_service",
    "sms_service",
]:
    sys.modules.setdefault(f"services.{mod}", getattr(getconnects_admin.services, mod))


@pytest.fixture(scope="session")
def app_module():
    import getconnects_admin
    app = getconnects_admin.create_app("testing")
    app.config["TESTING"] = True

    original_test_client = app.test_client

    def _client(*args, **kwargs):
        client = original_test_client(*args, **kwargs)
        with client.session_transaction() as sess:
            sess.setdefault("uid", "test")
            sess.setdefault("permissions", ["/"])
            sess.setdefault("is_staff", True)
        return client

    app.test_client = _client
    getconnects_admin.app = app
    return getconnects_admin


@pytest.fixture
def session(app_module):
    app_module.Base.metadata.drop_all(bind=app_module.engine)
    app_module.Base.metadata.create_all(bind=app_module.engine)
    db = app_module.SessionLocal()
    try:
        yield db
    finally:
        db.close()
