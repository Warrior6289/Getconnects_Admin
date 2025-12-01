"""Lead model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from . import Base


class Lead(Base):
    """A sales lead generated from a campaign."""

    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String)
    address = Column(String)
    email = Column(String)
    company = Column(String)
    secondary_phone = Column(String)
    lead_type = Column("disposition", String)
    caller_name = Column(String)
    caller_number = Column(String)
    notes = Column(String)
    client_id = Column(Integer, ForeignKey("clients.id"))
    campaign_id = Column(String, ForeignKey("campaigns.id"))
    number_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="leads")
    campaign = relationship("Campaign", back_populates="leads")


__all__ = ["Lead"]
