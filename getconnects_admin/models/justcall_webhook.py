"""JustCall webhook token storage and configuration."""

from sqlalchemy import Column, Integer, JSON, String
from sqlalchemy.orm import relationship

from . import Base


class JustCallWebhook(Base):
    """Stores webhook tokens and mapping info for incoming JustCall payloads."""

    __tablename__ = "justcall_webhooks"

    id = Column(Integer, primary_key=True)
    token = Column(String, unique=True, nullable=False)
    target_type = Column(String, nullable=False)
    mapping = Column(JSON)

    payloads = relationship(
        "JustCallWebhookPayload", back_populates="webhook", cascade="all, delete-orphan"
    )


__all__ = ["JustCallWebhook"]
