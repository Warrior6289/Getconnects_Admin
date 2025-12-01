"""Notification log model."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from . import Base


class NotificationLog(Base):
    """Stores results of notification attempts."""

    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    lead_id = Column(Integer, ForeignKey("leads.id"))
    channel = Column(String)
    status = Column(String)
    message = Column(String)

    # Convenience relationships for accessing related names in templates/API
    client = relationship("Client", lazy="joined")
    lead = relationship("Lead", lazy="joined")


__all__ = ["NotificationLog"]
