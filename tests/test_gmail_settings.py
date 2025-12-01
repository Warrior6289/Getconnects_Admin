import pytest

from models.gmail_credential import GmailCredential
from services.email_service import (
    GmailCredentialAuthenticationError,
    GmailCredentialSendError,
)


def test_gmail_api_credentials_encrypted(app_module, session, monkeypatch):
    monkeypatch.setattr(
        "getconnects_admin.routes.settings.verify_gmail_api_credentials",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "getconnects_admin.routes.settings.get_gmail_api_status",
        lambda *args, **kwargs: None,
    )

    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True

    client.post(
        "/settings/gmail",
        data={
            "action": "save_api",
            "api_client_id": "cid",
            "api_client_secret": "secret",
            "api_refresh_token": "refresh",
            "api_from_email": "from@example.com",
            "cc_emails": "cc1@example.com, cc2@example.com",
            "bcc_emails": "bcc@example.com",
        },
        follow_redirects=True,
    )

    creds = session.query(GmailCredential).first()
    assert creds.api_client_id == "cid"
    assert creds.api_client_secret == "secret"
    assert creds.api_refresh_token == "refresh"
    assert creds.api_from_email == "from@example.com"
    assert creds.username == "from@example.com"
    assert creds.cc_emails == "cc1@example.com,cc2@example.com"
    assert creds.bcc_emails == "bcc@example.com"
    assert creds._api_client_secret != "secret"
    assert creds._api_refresh_token != "refresh"


def test_gmail_settings_status_display(app_module, session, monkeypatch):
    monkeypatch.setattr(
        "getconnects_admin.routes.settings.verify_gmail_api_credentials",
        lambda *args, **kwargs: None,
    )

    status_cycle = [
        {"connected": False, "message": "Token expired"},
        {"connected": True, "message": "Connected"},
        None,
    ]

    def fake_status(*args, **kwargs):
        return status_cycle.pop(0)

    monkeypatch.setattr(
        "getconnects_admin.routes.settings.get_gmail_api_status",
        lambda *args, **kwargs: fake_status(),
    )

    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True

    resp = client.get("/settings/gmail")
    assert b"Token expired" in resp.data
    assert b"Needs attention" in resp.data

    resp = client.get("/settings/gmail")
    assert b"Connected" in resp.data
    assert b"badge-success" in resp.data

    resp = client.get("/settings/gmail")
    assert b"Not configured" in resp.data


@pytest.mark.parametrize(
    "exception_cls,expected_message",
    [
        (GmailCredentialAuthenticationError, b"Unable to verify Gmail API credentials"),
        (GmailCredentialSendError, b"Unable to verify Gmail API credentials"),
    ],
)
def test_gmail_api_validation_failures(
    app_module, session, monkeypatch, exception_cls, expected_message
):
    def _raise(*args, **kwargs):
        raise exception_cls("Unable to verify Gmail API credentials")

    monkeypatch.setattr(
        "getconnects_admin.routes.settings.verify_gmail_api_credentials",
        _raise,
    )
    monkeypatch.setattr(
        "getconnects_admin.routes.settings.get_gmail_api_status",
        lambda *args, **kwargs: None,
    )

    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True

    resp = client.post(
        "/settings/gmail",
        data={
            "action": "save_api",
            "api_client_id": "cid",
            "api_client_secret": "secret",
            "api_refresh_token": "refresh",
            "api_from_email": "from@example.com",
        },
        follow_redirects=True,
    )

    assert expected_message in resp.data
    assert session.query(GmailCredential).count() == 0
