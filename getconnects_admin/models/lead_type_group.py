"""Lead type group model."""

from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from . import Base


class LeadTypeGroup(Base):
    """A collection of lead types provided by JustCall."""

    __tablename__ = "disposition_groups"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)

    lead_types = relationship(
        "LeadType", back_populates="group", cascade="all, delete-orphan"
    )


__all__ = ["LeadTypeGroup"]
