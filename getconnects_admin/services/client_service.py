"""Business logic for client operations."""

from flask import current_app, flash

try:
    from ..models.client import Client
except ImportError:  # pragma: no cover - fallback for direct usage
    from models.client import Client
from .helpers import get_session


def list_clients() -> list[dict]:
    """Return all clients as a list of dictionaries."""

    with get_session() as session:
        results = []
        for c in session.query(Client).all():
            results.append(
                {
                    "id": c.id,
                    "company_name": c.company_name,
                    "contact_name": c.contact_name,
                    "contact_email": c.contact_email,
                    "phone": c.phone,
                    "created_at": c.created_at,
                }
            )
        return results


def create_client(
    company_name: str, contact_name: str, contact_email: str, phone: str
) -> bool:
    """Create a new :class:`Client` record in the database."""

    with get_session() as session:
        try:
            # Instantiate and persist the client model
            client = Client(
                company_name=company_name,
                contact_name=contact_name,
                contact_email=contact_email,
                phone=phone,
            )
            session.add(client)
            session.commit()
            return True
        except Exception as exc:  # pragma: no cover - logging side effects
            session.rollback()
            current_app.logger.error("Failed to create client: %s", exc)
            flash("Failed to create client")
            return False


def delete_client(client_id: int) -> bool:
    """Delete the specified client by id."""

    with get_session() as session:
        client = session.get(Client, client_id)
        if not client:
            flash("Client not found")
            return False
        try:
            session.delete(client)
            session.commit()
            return True
        except Exception as exc:  # pragma: no cover - logging side effects
            session.rollback()
            current_app.logger.error("Failed to delete client: %s", exc)
            flash("Failed to delete client")
            return False
