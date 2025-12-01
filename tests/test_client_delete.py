import pytest

from models.client import Client
from models.campaign import Campaign
from models.lead_type_group import LeadTypeGroup
from models.campaign_lead_type_group import CampaignLeadTypeGroup
from services.client_service import delete_client

def test_delete_client_removes_campaign_groups(session):
    client = Client(company_name='Acme', contact_name='John', contact_email='john@example.com', phone='123')
    group = LeadTypeGroup(id='g1', name='Group')
    campaign = Campaign(id='c1', campaign_name='Camp', status='active', client=client)
    mapping = CampaignLeadTypeGroup(campaign=campaign, group=group)
    session.add_all([client, group, campaign, mapping])
    session.commit()
    assert session.query(CampaignLeadTypeGroup).count() == 1

    # Use service to delete client which should cascade through campaigns
    assert delete_client(client.id)

    session.expire_all()
    assert session.query(Client).count() == 0
    assert session.query(Campaign).count() == 0
    assert session.query(CampaignLeadTypeGroup).count() == 0
