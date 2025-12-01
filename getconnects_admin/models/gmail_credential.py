"""Gmail credential storage with optional encryption."""

import os
from cryptography.fernet import Fernet
from sqlalchemy import Column, Integer, String

from . import Base


def _get_fernet() -> Fernet | None:
    key = os.getenv("ENCRYPTION_KEY")
    return Fernet(key.encode()) if key else None


def _encrypt(text: str) -> str:
    f = _get_fernet()
    return f.encrypt(text.encode()).decode() if f and text else text or ""


def _decrypt(token: str) -> str:
    f = _get_fernet()
    return f.decrypt(token.encode()).decode() if f and token else token or ""


class GmailCredential(Base):
    """Username and password for Gmail SMTP integration."""

    __tablename__ = "gmail_credentials"

    id = Column(Integer, primary_key=True)
    _username = Column("username", String, nullable=False)
    _password = Column("password", String, nullable=False)
    _from_email = Column("from_email", String, nullable=True)
    _cc_emails = Column("cc_emails", String, nullable=True)
    _bcc_emails = Column("bcc_emails", String, nullable=True)
    _api_client_id = Column("api_client_id", String, nullable=True)
    _api_client_secret = Column("api_client_secret", String, nullable=True)
    _api_refresh_token = Column("api_refresh_token", String, nullable=True)
    _api_from_email = Column("api_from_email", String, nullable=True)

    @property
    def username(self) -> str:
        return _decrypt(self._username)

    @username.setter
    def username(self, value: str) -> None:
        self._username = _encrypt(value)

    @property
    def password(self) -> str:
        return _decrypt(self._password)

    @password.setter
    def password(self, value: str) -> None:
        self._password = _encrypt(value)

    @property
    def from_email(self) -> str:
        return _decrypt(self._from_email)

    @from_email.setter
    def from_email(self, value: str) -> None:
        self._from_email = _encrypt(value)

    @property
    def cc_emails(self) -> str:
        return _decrypt(self._cc_emails)

    @cc_emails.setter
    def cc_emails(self, value: str) -> None:
        self._cc_emails = _encrypt(value)

    @property
    def bcc_emails(self) -> str:
        return _decrypt(self._bcc_emails)

    @bcc_emails.setter
    def bcc_emails(self, value: str) -> None:
        self._bcc_emails = _encrypt(value)

    @property
    def api_client_id(self) -> str:
        return _decrypt(self._api_client_id)

    @api_client_id.setter
    def api_client_id(self, value: str) -> None:
        self._api_client_id = _encrypt(value)

    @property
    def api_client_secret(self) -> str:
        return _decrypt(self._api_client_secret)

    @api_client_secret.setter
    def api_client_secret(self, value: str) -> None:
        self._api_client_secret = _encrypt(value)

    @property
    def api_refresh_token(self) -> str:
        return _decrypt(self._api_refresh_token)

    @api_refresh_token.setter
    def api_refresh_token(self, value: str) -> None:
        self._api_refresh_token = _encrypt(value)

    @property
    def api_from_email(self) -> str:
        return _decrypt(self._api_from_email)

    @api_from_email.setter
    def api_from_email(self, value: str) -> None:
        self._api_from_email = _encrypt(value)


__all__ = ["GmailCredential"]
