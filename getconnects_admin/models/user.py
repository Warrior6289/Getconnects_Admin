"""User model definition."""

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from . import Base


class User(Base):
    """Application user identified via Firebase UID."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_staff = Column(Boolean, default=False, nullable=False)

    permissions = relationship(
        "PagePermission", back_populates="user", cascade="all, delete-orphan"
    )


__all__ = ["User"]
