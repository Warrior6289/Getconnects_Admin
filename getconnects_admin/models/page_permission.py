"""Page permission model."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from . import Base


class PagePermission(Base):
    """Maps a user to an accessible page path."""

    __tablename__ = "page_permissions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    path = Column(String, nullable=False)

    user = relationship("User", back_populates="permissions")


__all__ = ["PagePermission"]
