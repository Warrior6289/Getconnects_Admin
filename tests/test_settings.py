from models.justcall_credential import JustCallCredential
import getconnects_admin.routes.settings
from models.notification_template import NotificationTemplate


def test_credentials_encrypted(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    client.post(
        "/settings/justcall",
        data={"api_key": "key", "api_secret": "secret"},
        follow_redirects=True,
    )
    creds = session.query(JustCallCredential).first()
    assert creds.api_key == "key"
    assert creds.api_secret == "secret"
    assert creds._api_key != "key"
    assert creds._api_secret != "secret"


def test_settings_ui_toggle(app_module, session, monkeypatch):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    resp = client.get("/settings/justcall")
    assert b"Save" in resp.data
    assert b"Delete Credentials" not in resp.data

    client.post(
        "/settings/justcall",
        data={"api_key": "key", "api_secret": "secret"},
        follow_redirects=True,
    )
    monkeypatch.setattr(
        getconnects_admin.routes.settings, "fetch_sms_numbers", lambda: []
    )
    resp = client.get("/settings/justcall")
    assert b"Delete Credentials" in resp.data
    assert b"Save Default Number" in resp.data
    assert b"********" in resp.data

    client.post(
        "/settings/justcall",
        data={"delete": "1"},
        follow_redirects=True,
    )
    resp = client.get("/settings/justcall")
    assert b"Save" in resp.data
    assert session.query(JustCallCredential).count() == 0


def test_can_save_default_sms_number(app_module, session, monkeypatch):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    client.post(
        "/settings/justcall",
        data={"api_key": "key", "api_secret": "secret"},
        follow_redirects=True,
    )
    monkeypatch.setattr(
        getconnects_admin.routes.settings, "fetch_sms_numbers", lambda: ["111", "222"]
    )
    client.post(
        "/settings/justcall",
        data={"save_number": "1", "sms_number": "222"},
        follow_redirects=True,
    )
    creds = session.query(JustCallCredential).first()
    assert creds.sms_number == "222"


def test_notification_template_placeholders(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    resp = client.get("/settings/templates")
    assert b"{name}" in resp.data
    assert b"{client_first_name}" in resp.data
    assert b"{notes}" in resp.data


def test_notification_template_edit(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True

    tmpl = NotificationTemplate(
        name="foo",
        sms_template="hi",
        email_subject="Initial subject",
        email_text="Initial body",
    )
    session.add(tmpl)
    session.commit()

    resp = client.get(f"/settings/templates/{tmpl.id}")
    assert b"Edit Notification Template" in resp.data

    resp = client.post(
        f"/settings/templates/{tmpl.id}",
        data={
            "name": "bar",
            "channel": "both",
            "sms_template": "hello",
            "email_subject": "Updated subject",
            "email_text": "Updated body",
        },
        follow_redirects=True,
    )
    assert b"Template updated" in resp.data
    session.expire_all()
    tmpl = session.get(NotificationTemplate, tmpl.id)
    assert tmpl.name == "bar"
    assert tmpl.sms_template == "hello"
    assert tmpl.email_subject == "Updated subject"
    assert tmpl.email_text == "Updated body"


def test_notification_template_email_defaults_in_form(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True

    tmpl = NotificationTemplate(
        name="with-email",
        sms_template="hi",
        email_subject="Subject",
        email_text="Body copy",
    )
    session.add(tmpl)
    session.commit()

    resp = client.get(f"/settings/templates/{tmpl.id}")
    assert b"Subject" in resp.data
    assert b"Body copy" in resp.data
