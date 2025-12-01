"""Client model."""

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from . import Base


class Client(Base):
    """Represents a business client using the platform."""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    contact_name = Column(String, nullable=False)
    contact_email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    leads = relationship(
        "Lead", back_populates="client", cascade="all, delete-orphan"
    )
    campaigns = relationship(
        "Campaign", back_populates="client", cascade="all, delete-orphan"
    )


__all__ = ["Client"]
