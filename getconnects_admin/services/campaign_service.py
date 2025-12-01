"""Business logic for campaign related operations."""

try:
    from ..models.campaign import Campaign
    from ..models.campaign_lead_type_group import CampaignLeadTypeGroup
    from ..models.lead_type_group import LeadTypeGroup
except ImportError:  # pragma: no cover
    from models.campaign import Campaign
    from models.campaign_lead_type_group import CampaignLeadTypeGroup
    from models.lead_type_group import LeadTypeGroup
from .helpers import get_session


def list_campaigns() -> list[dict]:
    """Return all campaigns as a list of dictionaries."""

    with get_session() as session:
        results = []
        for c in session.query(Campaign).all():
            groups = (
                session.query(LeadTypeGroup.name)
                .join(
                    CampaignLeadTypeGroup,
                    LeadTypeGroup.id
                    == CampaignLeadTypeGroup.lead_type_group_id,
                )
                .filter(CampaignLeadTypeGroup.campaign_id == c.id)
                .all()
            )
            group_names = sorted({name for (name,) in groups})

            results.append(
                {
                    "id": c.id,
                    "campaign_name": c.campaign_name,
                    "status": c.status,
                    "client_id": c.client_id,
                    "client_name": c.client.company_name if c.client else None,
                    "lead_type_groups": group_names,
                }
            )
        return results
