"""Utility helpers shared across service modules."""

from contextlib import contextmanager
from typing import Iterator

try:
    from ..models import SessionLocal
except ImportError:  # pragma: no cover
    from models import SessionLocal


@contextmanager
def get_session() -> Iterator[SessionLocal]:
    """Yield a database session and ensure it is properly closed.

    This helper centralises session management and avoids repetitive
    session creation and closing logic scattered across service functions.
    """

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
