"""Service functions for computing application statistics."""

import datetime
from sqlalchemy import func

try:
    from ..models.client import Client
    from ..models.campaign import Campaign
    from ..models.lead import Lead
except ImportError:  # pragma: no cover
    from models.client import Client
    from models.campaign import Campaign
    from models.lead import Lead
from .helpers import get_session


def get_stats() -> dict:
    """Aggregate basic counts used on the dashboard."""

    with get_session() as session:
        # Total counts for each primary model
        total_clients = session.query(func.count(Client.id)).scalar() or 0
        total_campaigns = session.query(func.count(Campaign.id)).scalar() or 0
        total_leads = session.query(func.count(Lead.id)).scalar() or 0

        # Calculate leads created within the last week
        week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        leads_week = (
            session.query(func.count(Lead.id))
            .filter(Lead.created_at >= week_ago)
            .scalar()
            or 0
        )

        return {
            "clients": total_clients,
            "campaigns": total_campaigns,
            "leads": total_leads,
            "leads_week": leads_week,
        }


def get_leads_by_campaign() -> list[dict]:
    """Return lead counts grouped by campaign.

    Each result contains the campaign name and the number of associated
    leads. Campaigns with no leads are included with a count of ``0``.
    """

    with get_session() as session:
        results = (
            session.query(Campaign.campaign_name, func.count(Lead.id))
            .outerjoin(Lead, Lead.campaign_id == Campaign.id)
            .group_by(Campaign.id)
            .all()
        )
        return [
            {"campaign": name, "leads": count} for name, count in results
        ]
