"""Client lead type notification settings model."""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from . import Base


class ClientLeadTypeSetting(Base):
    """Notification preferences for a client's lead types."""

    __tablename__ = "client_lead_type_settings"

    client_id = Column(Integer, ForeignKey("clients.id"), primary_key=True)
    lead_type_id = Column(
        String,
        ForeignKey("lead_types.id"),
        primary_key=True,
    )
    sms_enabled = Column(Boolean, default=False)
    email_enabled = Column(Boolean, default=False)
    sms_template = Column(Text)
    email_subject = Column(String)
    email_html = Column(Text)
    template_id = Column(Integer, ForeignKey("notification_templates.id"))

    client = relationship("Client")
    lead_type = relationship("LeadType")
    template = relationship("NotificationTemplate")


__all__ = ["ClientLeadTypeSetting"]
