"""Campaign model."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from . import Base


class Campaign(Base):
    """A marketing campaign associated with a client."""

    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, index=True)
    campaign_name = Column(String, nullable=False)
    status = Column(String)
    client_id = Column(Integer, ForeignKey("clients.id"))

    client = relationship("Client", back_populates="campaigns")
    leads = relationship(
        "Lead", back_populates="campaign", cascade="all, delete-orphan"
    )
    lead_type_groups = relationship(
        "CampaignLeadTypeGroup",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )


__all__ = ["Campaign"]
