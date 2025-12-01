import base64
import json
import os

import pytest

from models.gmail_credential import GmailCredential
import services.email_service as email_service


def _mock_gmail_requests(monkeypatch, expected_refresh_token="refresh", status_code=200):
    class DummyResponse:
        def __init__(self, code, payload):
            self.status_code = code
            self._payload = payload

        @property
        def ok(self):
            return 200 <= self.status_code < 300

        @property
        def text(self):
            return json.dumps(self._payload)

        def json(self):
            return self._payload

    sent_payloads: list[str] = []

    def fake_post(url, data=None, json=None, headers=None, timeout=10):
        if "oauth2" in url:
            assert data["refresh_token"] == expected_refresh_token
            if status_code != 200:
                return DummyResponse(status_code, {"error": "invalid_grant"})
            return DummyResponse(200, {"access_token": "token123"})

        assert headers["Authorization"] == "Bearer token123"
        sent_payloads.append(base64.urlsafe_b64decode(json["raw"].encode()).decode())
        return DummyResponse(status_code, {"id": "abc"})

    monkeypatch.setattr(email_service.requests, "post", fake_post)
    return sent_payloads


def test_send_email_uses_db_api_credentials(app_module, session, monkeypatch):
    session.add(
        GmailCredential(
            username="api@example.com",
            password="",
            api_client_id="cid",
            api_client_secret="secret",
            api_refresh_token="refresh",
            api_from_email="api@example.com",
            cc_emails="cc1@example.com,cc2@example.com",
            bcc_emails="bcc@example.com",
        )
    )
    session.commit()

    sent_payloads = _mock_gmail_requests(monkeypatch)

    assert email_service.send_email(
        "to@example.com", "Subject", "Body", html="<p>Body</p>"
    ) is True
    assert sent_payloads and "Subject" in sent_payloads[0]
    assert "cc1@example.com" in sent_payloads[0]
    assert "bcc@example.com" in sent_payloads[0]


def test_send_email_env_api_credentials(monkeypatch, app_module, session):
    os.environ["GMAIL_API_CLIENT_ID"] = "cid"
    os.environ["GMAIL_API_CLIENT_SECRET"] = "secret"
    os.environ["GMAIL_API_REFRESH_TOKEN"] = "refresh"
    os.environ["GMAIL_API_FROM_EMAIL"] = "api@example.com"

    sent_payloads = _mock_gmail_requests(monkeypatch)

    assert email_service.send_email("to@example.com", "Subject", "Body") is True
    assert sent_payloads and "Body" in sent_payloads[0]

    monkeypatch.delenv("GMAIL_API_CLIENT_ID", raising=False)
    monkeypatch.delenv("GMAIL_API_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GMAIL_API_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("GMAIL_API_FROM_EMAIL", raising=False)


def test_send_email_missing_sender(monkeypatch, app_module, session):
    session.query(GmailCredential).delete()
    session.commit()

    monkeypatch.setattr(email_service, "_get_env_credential", lambda key: None)

    sent_payloads = _mock_gmail_requests(monkeypatch)
    assert email_service.send_email("to@example.com", "Subject", "Body") is False
    assert sent_payloads == []


def test_verify_gmail_credentials_requires_address(monkeypatch):
    os.environ["GMAIL_API_CLIENT_ID"] = "cid"
    os.environ["GMAIL_API_CLIENT_SECRET"] = "secret"
    os.environ["GMAIL_API_REFRESH_TOKEN"] = "refresh"
    os.environ["GMAIL_API_FROM_EMAIL"] = "sender@example.com"

    sent_payloads = _mock_gmail_requests(monkeypatch)

    with pytest.raises(email_service.GmailCredentialSendError):
        email_service.verify_gmail_credentials("", "")

    email_service.verify_gmail_credentials("ignored", "", "sender@example.com")
    assert sent_payloads and "sender@example.com" in sent_payloads[0]

    for key in (
        "GMAIL_API_CLIENT_ID",
        "GMAIL_API_CLIENT_SECRET",
        "GMAIL_API_REFRESH_TOKEN",
        "GMAIL_API_FROM_EMAIL",
    ):
        os.environ.pop(key, None)


def test_get_gmail_api_status_connected(app_module, session, monkeypatch):
    creds = GmailCredential(
        username="sender@example.com",
        password="",
        api_client_id="cid",
        api_client_secret="secret",
        api_refresh_token="refresh",
        api_from_email="sender@example.com",
    )
    session.add(creds)
    session.commit()

    _mock_gmail_requests(monkeypatch)

    status = email_service.get_gmail_api_status(creds)
    assert status == {"connected": True, "message": "Connected to the Gmail API."}


def test_get_gmail_api_status_error(app_module, session, monkeypatch):
    creds = GmailCredential(
        username="sender@example.com",
        password="",
        api_client_id="cid",
        api_client_secret="secret",
        api_refresh_token="refresh",
        api_from_email="sender@example.com",
    )
    session.add(creds)
    session.commit()

    _mock_gmail_requests(monkeypatch, status_code=401)

    status = email_service.get_gmail_api_status(creds)
    assert status["connected"] is False
    assert "Unable to refresh" in status["message"] or "Failed to reach Gmail" in status["message"]
