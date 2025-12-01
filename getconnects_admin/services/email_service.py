from __future__ import annotations

"""Helper for sending emails through the Gmail REST API."""

import logging
import os
import base64
from email.message import EmailMessage

from flask import current_app
import requests

try:
    from ..models.gmail_credential import GmailCredential
except ImportError:  # pragma: no cover
    from models.gmail_credential import GmailCredential

from .helpers import get_session


def _logger():
    try:
        return current_app.logger
    except Exception:  # pragma: no cover - fallback when outside app context
        return logging.getLogger(__name__)


def _get_db_env_override(key: str) -> str | None:
    creds = _get_db_credentials()
    if not creds:
        return None

    mapping = {
        "GMAIL_API_CLIENT_ID": creds.api_client_id,
        "GMAIL_API_CLIENT_SECRET": creds.api_client_secret,
        "GMAIL_API_REFRESH_TOKEN": creds.api_refresh_token,
        "GMAIL_API_FROM_EMAIL": creds.api_from_email or creds.from_email,
    }
    value = mapping.get(key)
    return value or None


def _get_env_credential(key: str) -> str | None:
    """Fetch *key* from environment, the database, or an optional secret store."""

    value = os.environ.get(key)
    if value:
        return value

    db_value = _get_db_env_override(key)
    if db_value:
        return db_value
    try:  # pragma: no cover - secret store is optional
        from .secret_store import get_secret  # type: ignore

        return get_secret(key)
    except Exception:
        return None


def _get_db_credentials() -> GmailCredential | None:
    with get_session() as session:
        return session.query(GmailCredential).first()


class GmailCredentialError(Exception):
    """Base class for Gmail credential verification failures."""


class GmailCredentialAuthenticationError(GmailCredentialError):
    """Raised when Gmail rejects the supplied credentials."""


class GmailCredentialSendError(GmailCredentialError):
    """Raised when Gmail accepts the login but sending fails."""


def verify_gmail_credentials(
    username: str, password: str, from_email: str | None = None
) -> None:
    """Validate Gmail connectivity using OAuth-based delivery."""

    recipient = from_email or username
    _verify_with_gmail_api(recipient)


def _get_api_credentials() -> dict[str, str | None]:
    return {
        "client_id": _get_env_credential("GMAIL_API_CLIENT_ID"),
        "client_secret": _get_env_credential("GMAIL_API_CLIENT_SECRET"),
        "refresh_token": _get_env_credential("GMAIL_API_REFRESH_TOKEN"),
        "user_email": _get_env_credential("GMAIL_API_FROM_EMAIL"),
    }


def verify_gmail_api_credentials(
    client_id: str, client_secret: str, refresh_token: str, from_email: str | None
) -> None:
    """Validate the Gmail API OAuth credentials by refreshing a token."""

    if not client_id or not client_secret or not refresh_token:
        raise GmailCredentialAuthenticationError(
            "Client ID, client secret, and refresh token are required."
        )
    if not (from_email or _get_db_env_override("GMAIL_API_FROM_EMAIL")):
        raise GmailCredentialAuthenticationError(
            "A sending email address is required for Gmail API delivery."
        )

    credentials = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "user_email": from_email,
    }

    _refresh_access_token(credentials)


def _refresh_access_token(credentials: dict[str, str | None]) -> str:
    missing = [
        key
        for key in ("client_id", "client_secret", "refresh_token")
        if not credentials.get(key)
    ]
    if missing:
        raise GmailCredentialAuthenticationError(
            "Gmail API credentials are not configured (missing {}).".format(
                ", ".join(missing)
            )
        )

    try:
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": credentials["client_id"],
                "client_secret": credentials["client_secret"],
                "refresh_token": credentials["refresh_token"],
                "grant_type": "refresh_token",
            },
            timeout=10,
        )
    except requests.RequestException as exc:  # pragma: no cover - network failure
        raise GmailCredentialSendError(f"Failed to refresh Gmail access token: {exc}") from exc

    if response.status_code != 200:
        detail: str
        try:
            payload = response.json()
            detail = payload.get("error_description") or payload.get("error") or response.text
        except ValueError:
            detail = response.text
        raise GmailCredentialAuthenticationError(
            f"Unable to refresh Gmail access token: {detail}"
        )

    try:
        payload = response.json()
    except ValueError as exc:  # pragma: no cover - unexpected response
        raise GmailCredentialAuthenticationError("Invalid Gmail token response") from exc

    access_token = payload.get("access_token")
    if not access_token:
        raise GmailCredentialAuthenticationError("Gmail token response missing access_token")
    return str(access_token)


def _send_with_gmail_api(
    msg: EmailMessage, credentials: dict[str, str | None] | None = None
) -> None:
    credentials = credentials or _get_api_credentials()
    access_token = _refresh_access_token(credentials)

    encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        response = requests.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"raw": encoded_message},
            timeout=10,
        )
    except requests.RequestException as exc:  # pragma: no cover - network failure
        raise GmailCredentialSendError(f"Failed to call Gmail API: {exc}") from exc

    if response.status_code == 401:
        raise GmailCredentialAuthenticationError(
            "Gmail API rejected the access token; refresh the OAuth credentials"
        )

    if not response.ok:
        try:
            payload = response.json()
            detail = (
                payload.get("error", {}).get("message")
                if isinstance(payload.get("error"), dict)
                else payload.get("error")
            )
        except ValueError:
            detail = None
        message = detail or response.text or "Unknown error"
        raise GmailCredentialSendError(f"Gmail API send failed: {message}")


def _verify_with_gmail_api(recipient: str | None) -> None:
    if not recipient:
        raise GmailCredentialSendError(
            "A from email address is required when using the Gmail API delivery mode"
        )

    msg = EmailMessage()
    msg["From"] = recipient
    msg["To"] = recipient
    msg["Subject"] = "Gmail credentials verification"
    msg.set_content(
        "This message confirms your Gmail account can send emails via GetConnects."
    )

    _send_with_gmail_api(msg)


def send_email(to_email: str, subject: str, body: str, *, html: str | None = None) -> bool:
    """Send an email using the Gmail REST API."""

    creds = _get_db_credentials()
    if creds:
        from_email = creds.api_from_email or creds.from_email or creds.username
        cc_emails = creds.cc_emails
        bcc_emails = creds.bcc_emails
        api_credentials = {
            "client_id": creds.api_client_id,
            "client_secret": creds.api_client_secret,
            "refresh_token": creds.api_refresh_token,
            "user_email": creds.api_from_email or creds.from_email or creds.username,
        }
    else:
        from_email = _get_env_credential("GMAIL_API_FROM_EMAIL")
        cc_emails = None
        bcc_emails = None
        api_credentials = _get_api_credentials()

    if not from_email:
        _logger().error("Gmail sender address not configured")
        return False

    msg = EmailMessage()
    msg["From"] = from_email or ""
    msg["To"] = to_email
    msg["Subject"] = subject
    if cc_emails:
        msg["Cc"] = cc_emails
    if bcc_emails:
        msg["Bcc"] = bcc_emails
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        _send_with_gmail_api(msg, api_credentials)
        return True
    except GmailCredentialAuthenticationError as exc:
        _logger().error("Failed to authenticate with Gmail: %s", exc)
    except GmailCredentialSendError as exc:
        _logger().error("Failed to send email: %s", exc)
    return False


def get_gmail_api_status(
    credentials: GmailCredential | None = None,
) -> dict[str, str] | None:
    """Return the connection status for stored Gmail API credentials."""

    creds = credentials or _get_db_credentials()
    if not creds:
        return None

    api_credentials = {
        "client_id": creds.api_client_id,
        "client_secret": creds.api_client_secret,
        "refresh_token": creds.api_refresh_token,
        "user_email": creds.api_from_email or creds.from_email or creds.username,
    }

    if not all(
        (
            api_credentials["client_id"],
            api_credentials["client_secret"],
            api_credentials["refresh_token"],
            api_credentials["user_email"],
        )
    ):
        return None

    try:
        _refresh_access_token(api_credentials)
    except GmailCredentialAuthenticationError as exc:
        message = str(exc) or "Unable to refresh Gmail access token."
        return {"connected": False, "message": message}
    except GmailCredentialSendError as exc:
        message = str(exc) or "Failed to reach Gmail to refresh the access token."
        return {"connected": False, "message": message}

    return {"connected": True, "message": "Connected to the Gmail API."}
