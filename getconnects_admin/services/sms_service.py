from __future__ import annotations

"""Helper for sending SMS messages via the JustCall API."""

import logging
import os

import requests
from flask import current_app

try:
    from ..models.justcall_credential import JustCallCredential
except ImportError:  # pragma: no cover
    from models.justcall_credential import JustCallCredential

from .helpers import get_session

JUSTCALL_SMS_URL = "https://api.justcall.io/v2.1/texts/new"
JUSTCALL_NUMBERS_URL = "https://api.justcall.io/v2.1/phone-numbers"


def _logger():
    try:
        return current_app.logger
    except Exception:  # pragma: no cover - fallback when outside app context
        return logging.getLogger(__name__)


def send_sms(to_number: str, message: str, from_number: str | None = None) -> bool:
    """Send an SMS via JustCall.

    Parameters
    ----------
    to_number: str
        Destination phone number including country code.
    message: str
        Body of the SMS message.
    from_number: str | None, optional
        Specific JustCall number to send the SMS from. If ``None`` the
        default number configured in the JustCall account will be used.
    """

    with get_session() as session:
        creds = session.query(JustCallCredential).first()
    if creds:
        api_key, api_secret = creds.api_key, creds.api_secret
        if from_number is None and creds.sms_number:
            from_number = creds.sms_number
    else:
        api_key = os.getenv("JUSTCALL_API_KEY")
        api_secret = os.getenv("JUSTCALL_API_SECRET")
        if not api_key or not api_secret:
            _logger().error("JustCall credentials not configured")
            return False

    payload = {"contact_number": to_number, "body": message}
    if from_number:
        payload["justcall_number"] = from_number

    try:  # pragma: no cover - network call
        resp = requests.post(
            JUSTCALL_SMS_URL,
            json=payload,
            auth=(api_key, api_secret),
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:  # pragma: no cover - network errors
        _logger().error("Failed to send SMS: %s", exc)
        return False


def fetch_sms_numbers() -> list[str]:
    """Return all JustCall numbers available for sending SMS.

    The function queries the JustCall API using stored credentials or
    environment variables. It returns a simple list of phone numbers in
    E.164 format. Any errors are logged and result in an empty list.
    """

    with get_session() as session:
        creds = session.query(JustCallCredential).first()
    if creds:
        api_key, api_secret = creds.api_key, creds.api_secret
    else:
        api_key = os.getenv("JUSTCALL_API_KEY")
        api_secret = os.getenv("JUSTCALL_API_SECRET")
        if not api_key or not api_secret:
            _logger().error("JustCall credentials not configured")
            return []

    try:  # pragma: no cover - network call
        resp = requests.get(
            JUSTCALL_NUMBERS_URL, auth=(api_key, api_secret), timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        numbers: list[str] = []

        if isinstance(data, list):
            raw_numbers = data
        else:
            raw_numbers = data.get("numbers")
            if raw_numbers is None:
                inner = data.get("data", {})
                if isinstance(inner, dict):
                    raw_numbers = inner.get("numbers") or inner.get("data", {}).get("numbers")
                elif isinstance(inner, list):
                    raw_numbers = inner
                else:
                    raw_numbers = []

        def _to_e164(number: str) -> str:
            """Return *number* normalised to E.164 format."""
            digits = "".join(ch for ch in str(number) if ch.isdigit())
            if not digits:
                return ""
            return "+" + digits

        for item in raw_numbers:
            num = None
            if isinstance(item, dict):
                friendly = item.get("friendly_number")
                if friendly and "+" in friendly:
                    num = _to_e164(friendly)
                if not num:
                    for key in (
                        "justcall_number",
                        "phone_number",
                        "number",
                        "friendly_number",
                    ):
                        val = item.get(key)
                        if val:
                            num = _to_e164(val)
                            break
            else:
                num = _to_e164(item)
            if num:
                numbers.append(num)
        return numbers
    except Exception as exc:  # pragma: no cover - network errors
        _logger().error("Failed to fetch JustCall numbers: %s", exc)
        return []
