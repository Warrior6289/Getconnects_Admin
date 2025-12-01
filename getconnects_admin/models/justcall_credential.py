"""JustCall API credential storage with optional encryption."""

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


class JustCallCredential(Base):
    """API credentials for JustCall integration."""

    __tablename__ = "justcall_credentials"

    id = Column(Integer, primary_key=True)
    _api_key = Column("api_key", String, nullable=False)
    _api_secret = Column("api_secret", String, nullable=False)
    sms_number = Column(String, nullable=True)

    @property
    def api_key(self) -> str:
        return _decrypt(self._api_key)

    @api_key.setter
    def api_key(self, value: str) -> None:
        self._api_key = _encrypt(value)

    @property
    def api_secret(self) -> str:
        return _decrypt(self._api_secret)

    @api_secret.setter
    def api_secret(self, value: str) -> None:
        self._api_secret = _encrypt(value)


__all__ = ["JustCallCredential"]

