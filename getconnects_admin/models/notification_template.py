"""Reusable notification templates for SMS and email."""

from sqlalchemy import Boolean, Column, Integer, String, Text

from . import Base


class NotificationTemplate(Base):
    """A named template that can be applied to notifications."""

    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    sms_template = Column(Text)
    email_subject = Column(String)
    email_text = Column(Text)
    email_html = Column(Text)
    is_default = Column(Boolean, default=False)


__all__ = ["NotificationTemplate"]
