from requests.exceptions import RequestException

from services.justcall_service import fetch_campaigns, sync_campaigns
from models.campaign import Campaign
from models.campaign_lead_type import CampaignLeadType
from models.campaign_lead_type_group import CampaignLeadTypeGroup
from models.lead_type import LeadType
from models.lead_type_group import LeadTypeGroup


def sample_data():
    return [
        {
            "id": "c1",
            "name": "Campaign One",
            "status": "active",
            "disposition_groups": [
                {
                    "id": "g1",
                    "name": "Group 1",
                    "dispositions": [
                        {"id": "d1", "name": "Interested"},
                        {"id": "d2", "name": "Not Interested"},
                    ],
                }
            ],
        }
    ]


def test_sync_campaigns_idempotent(app_module, session):
    data = sample_data()
    sync_campaigns(data)
    assert session.query(Campaign).filter_by(id="c1").count() == 1
    assert session.query(LeadTypeGroup).count() == 1
    assert session.query(LeadType).count() == 2
    assert session.query(CampaignLeadType).count() == 2

    # Calling again should not create duplicates
    sync_campaigns(data)
    assert session.query(Campaign).filter_by(id="c1").count() == 1
    assert session.query(LeadTypeGroup).count() == 1
    assert session.query(LeadType).count() == 2
    assert session.query(CampaignLeadType).count() == 2


def sample_data_group_id_only():
    return [
        {
            "id": "c2",
            "name": "Campaign Two",
            "status": "active",
            "disposition_groups": ["g2"],
        }
    ]


def test_sync_campaigns_with_group_id_only(app_module, session):
    data = sample_data_group_id_only()
    sync_campaigns(data)

    assert session.query(Campaign).filter_by(id="c2").count() == 1
    assert session.query(LeadTypeGroup).count() == 1
    assert session.query(CampaignLeadTypeGroup).count() == 1
    assert session.query(LeadType).count() == 0
    assert session.query(CampaignLeadType).count() == 0


def sample_data_duplicate_groups():
    return [
        {
            "id": "c3",
            "name": "Campaign Duplicate",
            "status": "active",
            "disposition_groups": [
                {"id": "g3", "name": "Dup Group"},
                {"id": "g3", "name": "Dup Group"},
            ],
        }
    ]


def test_sync_campaigns_with_duplicate_groups(app_module, session):
    data = sample_data_duplicate_groups()
    sync_campaigns(data)

    assert session.query(Campaign).filter_by(id="c3").count() == 1
    assert session.query(LeadTypeGroup).count() == 1
    assert session.query(CampaignLeadTypeGroup).count() == 1
def sample_data_duplicate_dispositions():
    return [
        {
            "id": "c4",
            "name": "Campaign With Dup Dispositions",
            "status": "active",
            "disposition_groups": [
                {
                    "id": "g4",
                    "name": "Group 4",
                    "dispositions": [
                        {"id": "d4", "name": "Call Back"},
                        {"id": "d4", "name": "Call Back"},
                    ],
                }
            ],
        }
    ]


def test_sync_campaigns_with_duplicate_dispositions(app_module, session):
    data = sample_data_duplicate_dispositions()
    sync_campaigns(data)

    assert session.query(Campaign).filter_by(id="c4").count() == 1
    assert session.query(LeadTypeGroup).count() == 1
    assert session.query(LeadType).count() == 1
    assert session.query(CampaignLeadType).count() == 1


def test_fetch_campaigns_request_exception(monkeypatch, caplog):
    def mock_get(*args, **kwargs):
        raise RequestException("boom")

    monkeypatch.setattr("services.justcall_service.requests.get", mock_get)

    with caplog.at_level("ERROR"):
        campaigns = fetch_campaigns("api-key", "api-secret")

    assert campaigns == []
    assert any(
        "Failed to fetch campaigns from JustCall API" in record.getMessage()
        for record in caplog.records
    )

