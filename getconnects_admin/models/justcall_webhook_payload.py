"""Stores incoming JustCall webhook payloads for testing and mapping."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, func
from sqlalchemy.orm import relationship

from . import Base


class JustCallWebhookPayload(Base):
    """Log of payloads received for a given JustCall webhook token."""

    __tablename__ = "justcall_webhook_payloads"

    id = Column(Integer, primary_key=True)
    token_id = Column(Integer, ForeignKey("justcall_webhooks.id"), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    webhook = relationship("JustCallWebhook", back_populates="payloads")


__all__ = ["JustCallWebhookPayload"]
