"""Association between campaigns and lead type groups."""

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from . import Base


class CampaignLeadTypeGroup(Base):
    """Mapping between a campaign and a lead type group."""

    __tablename__ = "campaign_disposition_groups"

    campaign_id = Column(String, ForeignKey("campaigns.id"), primary_key=True)
    lead_type_group_id = Column(
        "disposition_group_id",
        String,
        ForeignKey("disposition_groups.id"),
        primary_key=True,
    )

    campaign = relationship("Campaign", back_populates="lead_type_groups")
    group = relationship("LeadTypeGroup")


__all__ = ["CampaignLeadTypeGroup"]
