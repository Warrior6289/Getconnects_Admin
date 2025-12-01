"""Lead type model."""

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from . import Base


class LeadType(Base):
    """A single lead type within a group."""

    __tablename__ = "lead_types"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    group_id = Column(String, ForeignKey("disposition_groups.id"))

    group = relationship("LeadTypeGroup", back_populates="lead_types")


__all__ = ["LeadType"]
