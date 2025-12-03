"""Campaign lead type mapping model."""

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from . import Base


class CampaignLeadType(Base):
    """Mapping between a campaign and its lead types."""

    __tablename__ = "campaign_lead_types"

    campaign_id = Column(String, ForeignKey("campaigns.id"), primary_key=True)
    lead_type_id = Column(
        String,
        ForeignKey("lead_types.id"),
        primary_key=True,
    )
    lead_type_name = Column(String)
    sms_enabled = Column(Boolean)
    email_enabled = Column(Boolean)

    lead_type = relationship("LeadType")


__all__ = ["CampaignLeadType"]
