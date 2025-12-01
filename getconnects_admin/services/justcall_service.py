"""Integration with the JustCall API.

This module provides helper functions to retrieve campaigns and
synchronise them with the local database. Only a subset of the JustCall
API is implemented and the functions are intentionally simple so they can
be easily mocked during tests.
"""

from __future__ import annotations

import base64
import logging
import requests

try:
    from ..models.campaign import Campaign
    from ..models.campaign_lead_type import CampaignLeadType
    from ..models.campaign_lead_type_group import CampaignLeadTypeGroup
    from ..models.lead_type import LeadType
    from ..models.lead_type_group import LeadTypeGroup
except ImportError:  # pragma: no cover
    from models.campaign import Campaign
    from models.campaign_lead_type import CampaignLeadType
    from models.campaign_lead_type_group import CampaignLeadTypeGroup
    from models.lead_type import LeadType
    from models.lead_type_group import LeadTypeGroup
from .helpers import get_session

# Base URL for the JustCall Sales Dialer API
JUSTCALL_API_BASE = "https://api.justcall.io/v2.1/sales_dialer"

logger = logging.getLogger(__name__)


def fetch_campaigns(api_key: str, api_secret: str) -> list[dict]:
    """Fetch campaigns from the JustCall Sales Dialer API.

    Parameters
    ----------
    api_key: str
        JustCall API key.
    api_secret: str
        JustCall API secret.
    """

    encoded_key_secret = base64.b64encode(
        f"{api_key}:{api_secret}".encode()
    ).decode()
    headers = {"Authorization": f"Basic {encoded_key_secret}"}
    try:
        resp = requests.get(
            f"{JUSTCALL_API_BASE}/campaigns", headers=headers, timeout=10
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException:
        logger.exception("Failed to fetch campaigns from JustCall API")
        return []
    return resp.json().get("data", [])


def sync_campaigns(campaigns: list[dict]) -> None:
    """Synchronise campaign and lead type data into the database.

    Existing campaigns, lead type groups and lead types are updated in
    place; new objects are created as needed. The function is idempotent so
    running it multiple times with the same data will not create
    duplicates.
    """

    with get_session() as session:
        for camp in campaigns:
            campaign_id = str(camp.get("id"))
            campaign = session.get(Campaign, campaign_id)
            if campaign is None:
                campaign = Campaign(
                    id=campaign_id,
                    campaign_name=camp.get("name", ""),
                    status=camp.get("status"),
                )
                session.add(campaign)
                session.flush()
            else:
                campaign.campaign_name = camp.get("name", "")
                campaign.status = camp.get("status")

            groups_info = camp.get("disposition_groups")
            if groups_info is None:
                group_info = (
                    camp.get("disposition_group")
                    or camp.get("disposition_group_id")
                )
                groups_info = [group_info] if group_info else []

            seen_groups = set()
            for group_info in groups_info:
                if isinstance(group_info, dict):
                    group_id = group_info.get("id")
                    if not group_id:
                        continue
                    group_id = str(group_id)
                    if group_id in seen_groups:
                        continue
                    seen_groups.add(group_id)
                    group_name = group_info.get("name", "")
                    dispositions = group_info.get("dispositions", [])
                else:
                    if not group_info:
                        continue
                    group_id = str(group_info)
                    if group_id in seen_groups:
                        continue
                    seen_groups.add(group_id)
                    group_name = camp.get("disposition_group_name", "")
                    dispositions = []

                dg = session.get(LeadTypeGroup, group_id)
                if dg is None:
                    dg = LeadTypeGroup(id=group_id, name=group_name)
                    session.add(dg)
                elif group_name:
                    dg.name = group_name

                if not session.get(
                    CampaignLeadTypeGroup, (campaign.id, dg.id)
                ):
                    session.add(
                        CampaignLeadTypeGroup(
                            campaign_id=campaign.id, lead_type_group_id=dg.id
                        )
                    )

                seen_disps = set()
                for disp in dispositions:

                    disp_id = disp.get("id")
                    if not disp_id:
                        continue
                    disp_id = str(disp_id)
                    if disp_id in seen_disps:
                        continue
                    seen_disps.add(disp_id)

                    d = session.get(LeadType, disp_id)
                    if d is None:
                        d = LeadType(
                            id=disp_id,
                            name=disp.get("name", ""),
                            group=dg,
                        )
                        session.add(d)

                    if not session.get(
                        CampaignLeadType, (campaign.id, d.id)
                    ):
                        session.add(
                            CampaignLeadType(
                                campaign_id=campaign.id,
                                lead_type_id=d.id,
                                lead_type_name=d.name,
                                sms_enabled=False,
                                email_enabled=False,
                            )
                        )
        session.commit()
