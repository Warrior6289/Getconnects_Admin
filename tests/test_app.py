import csv
import datetime
import io
from types import SimpleNamespace

from models.campaign_lead_type import CampaignLeadType
from models.campaign_lead_type_group import CampaignLeadTypeGroup
from models.lead_type import LeadType
from models.lead_type_group import LeadTypeGroup
from models.client_lead_type_setting import ClientLeadTypeSetting


def test_client_crud(app_module, session):
    # create
    assert app_module.create_client("Acme", "Alice", "a@example.com", "111")

    # read
    clients = app_module.list_clients()
    assert len(clients) == 1
    client_id = clients[0]["id"]
    assert clients[0]["created_at"] is not None

    # update
    client = session.get(app_module.Client, client_id)
    client.contact_name = "Alicia"
    session.commit()
    updated = session.get(app_module.Client, client_id)
    assert updated.contact_name == "Alicia"

    # delete
    session.delete(updated)
    session.commit()
    assert session.query(app_module.Client).count() == 0


def test_lead_crud(app_module, session):
    """Basic create, read, update, delete operations for leads."""
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(
        id="camp1", campaign_name="Camp", client=client
    )
    session.add_all([client, campaign])
    session.commit()

    assert app_module.create_lead(
        "Bob",
        "222",
        "b@example.com",
        campaign_id=campaign.id,
        lead_type="lt1",
        notes="Caller left a note",
    )
    leads = app_module.list_leads()
    assert len(leads) == 1
    assert leads[0]["notes"] == "Caller left a note"
    lead_id = leads[0]["id"]

    lead = session.get(app_module.Lead, lead_id)
    lead.name = "Bobby"
    session.commit()
    updated = session.get(app_module.Lead, lead_id)
    assert updated.name == "Bobby"

    session.delete(updated)
    session.commit()
    assert session.query(app_module.Lead).count() == 0


def test_list_campaigns_includes_lead_type_groups(app_module, session):
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(
        id="camp1", campaign_name="Camp", client=client
    )
    group = LeadTypeGroup(id="g1", name="Group1")
    cltg = CampaignLeadTypeGroup(
        campaign_id=campaign.id, lead_type_group_id=group.id
    )
    session.add_all([client, campaign, group, cltg])
    session.commit()

    campaigns = app_module.list_campaigns()
    assert campaigns[0]["lead_type_groups"] == ["Group1"]


def test_get_stats(app_module, session):
    assert app_module.create_client("Acme", "Alice", "a@example.com", "111")
    client = session.query(app_module.Client).first()
    camp = app_module.Campaign(
        id="camp1", campaign_name="Camp", client_id=client.id
    )
    session.add(camp)
    session.commit()
    session.add(
        app_module.Lead(name="L1", client_id=client.id, campaign_id=camp.id)
    )
    old_date = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    session.add(
        app_module.Lead(
            name="Old",
            client_id=client.id,
            campaign_id=camp.id,
            created_at=old_date,
        )
    )
    session.commit()
    stats = app_module.get_stats()
    assert stats["clients"] == 1
    assert stats["campaigns"] == 1
    assert stats["leads"] == 2
    assert stats["leads_week"] == 1


def test_verify_supabase_token(app_module, monkeypatch):
    def fake_get_user(token):
        if token == "good":
            user = SimpleNamespace(id="123", email="a@example.com")
            return SimpleNamespace(user=user)
        raise Exception("bad token")

    fake_client = SimpleNamespace(auth=SimpleNamespace(get_user=fake_get_user))
    import services.auth_service as auth_service
    monkeypatch.setattr(auth_service, "_get_supabase_client", lambda: fake_client)
    assert app_module.verify_supabase_token("good") == {"sub": "123", "email": "a@example.com"}
    assert app_module.verify_supabase_token("bad") is None


def test_dashboard_route(app_module, session):
    session.add(
        app_module.Client(
            company_name="Acme",
            contact_name="Alice",
            contact_email="a@example.com",
            phone="111",
        )
    )
    session.commit()
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
    resp = client.get("/", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data
    assert b"Acme" in resp.data


def test_leads_page_allows_adding_lead(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(
        id="camp1", campaign_name="Camp", client=client
    )
    lead_type = LeadType(id="lt1", name="Lead1")
    clt = CampaignLeadType(campaign_id=campaign.id, lead_type_id=lead_type.id)
    session.add_all([client, campaign, lead_type, clt])
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"
    resp = test_client.post(
        "/leads",
        data={
            "name": "Bob",
            "phone": "222",
            "email": "b@example.com",
            "campaign_id": campaign.id,
            "lead_type": lead_type.name,
            "notes": "",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Bob" in resp.data


def test_leads_page_allows_csv_import(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(
        id="camp1", campaign_name="Camp", client=client
    )
    lead_type = LeadType(id="lt1", name="Lead1")
    clt = CampaignLeadType(campaign_id=campaign.id, lead_type_id=lead_type.id)
    session.add_all([client, campaign, lead_type, clt])
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"
    csv_data = (
        "name,phone,email,campaign,lead_type\n"
        "Bob,222,b@example.com,Camp,Lead1\n"
    )
    data = {
        "file": (io.BytesIO(csv_data.encode()), "leads.csv"),
        "name_column": "name",
        "phone_column": "phone",
        "email_column": "email",
        "campaign_id_column": "campaign",
        "lead_type_column": "lead_type",
        "notes_column": "",
        "consent": "y",
    }
    resp = test_client.post(
        "/leads/import",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200


def test_import_autodetects_columns(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(
        id="camp1", campaign_name="Camp", client=client
    )
    lead_type = LeadType(id="lt1", name="Lead1")
    clt = CampaignLeadType(campaign_id=campaign.id, lead_type_id=lead_type.id)
    session.add_all([client, campaign, lead_type, clt])
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"
    csv_data = (
        "Name,Phone,Email,Address,Company,Secondary Number,"
        "Campaign,Lead Type,Caller,Calling Number\n"
        "Bob,222,b@example.com,Street,Acme,999999,Camp,Lead1,Alice,12345\n"
    )
    data = {
        "file": (io.BytesIO(csv_data.encode()), "leads.csv"),
        "name_column": "",
        "phone_column": "",
        "consent": "y",
        "notes_column": "",
    }
    resp = test_client.post(
        "/leads/import",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    leads = app_module.list_leads()
    assert leads[0]["email"] == "b@example.com"
    assert leads[0]["address"] == "Street"
    assert leads[0]["company"] == "Acme"
    assert leads[0]["secondary_phone"] == "999999"
    assert leads[0]["caller_name"] == "Alice"
    assert leads[0]["caller_number"] == "12345"
    assert leads[0]["campaign_id"] == campaign.id
    assert leads[0]["lead_type"] == "Lead1"
    assert b"Bob" in resp.data


def test_import_autodetects_alternate_headers(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(
        id="camp1", campaign_name="Camp", client=client
    )
    lead_type = LeadType(id="lt1", name="Lead1")
    clt = CampaignLeadType(campaign_id=campaign.id, lead_type_id=lead_type.id)
    session.add_all([client, campaign, lead_type, clt])
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"
    csv_data = (
        "Client Number,Client Name,Email,Address,Company,"
        "Alternate Phone Number,Campaign Name,Justcall Number,"
        "Teammate,Disposition Code\n"
        "222,Bob,b@example.com,Street,Acme,999999,Camp,12345,Alice,Lead1\n"
    )
    data = {
        "file": (io.BytesIO(csv_data.encode()), "leads.csv"),
        "name_column": "",
        "phone_column": "",
        "consent": "y",
        "notes_column": "",
    }
    resp = test_client.post(
        "/leads/import",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    leads = app_module.list_leads()
    assert leads[0]["name"] == "Bob"
    assert leads[0]["phone"] == "222"
    assert leads[0]["secondary_phone"] == "999999"
    assert leads[0]["campaign_id"] == campaign.id
    assert leads[0]["lead_type"] == "Lead1"
    assert leads[0]["caller_name"] == "Alice"
    assert leads[0]["caller_number"] == "12345"


def test_import_fails_with_unknown_campaign(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    lead_type = LeadType(id="lt1", name="Lead1")
    session.add(lead_type)
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"
    csv_data = "name,phone,campaign,lead_type\nBob,222,NoCamp,Lead1\n"
    data = {
        "file": (io.BytesIO(csv_data.encode()), "leads.csv"),
        "name_column": "name",
        "phone_column": "phone",
        "campaign_id_column": "campaign",
        "lead_type_column": "lead_type",
        "consent": "y",
        "notes_column": "",
    }
    resp = test_client.post(
        "/leads/import",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"Unknown campaign" in resp.data
    leads = app_module.list_leads()
    assert leads == []


def test_import_fails_with_unknown_lead_type(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(
        id="camp1", campaign_name="Camp", client=client
    )
    lead_type = LeadType(id="lt1", name="Lead1")
    clt = CampaignLeadType(campaign_id=campaign.id, lead_type_id=lead_type.id)
    session.add_all([client, campaign, lead_type, clt])
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"
    csv_data = "name,phone,campaign,lead_type\nBob,222,Camp,BadType\n"
    data = {
        "file": (io.BytesIO(csv_data.encode()), "leads.csv"),
        "name_column": "name",
        "phone_column": "phone",
        "campaign_id_column": "campaign",
        "lead_type_column": "lead_type",
        "consent": "y",
        "notes_column": "",
    }
    resp = test_client.post(
        "/leads/import",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"Unknown lead type" in resp.data
    leads = app_module.list_leads()
    assert leads == []


def test_leads_page_allows_edit_and_delete(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(
        id="camp1", campaign_name="Camp", client=client
    )
    lead_type = LeadType(id="lt1", name="Lead1")
    session.add_all([client, campaign, lead_type])
    session.commit()

    lead = app_module.Lead(
        name="Bob",
        phone="222",
        email="b@example.com",
        campaign_id=campaign.id,
        lead_type=lead_type.name,
    )
    session.add(lead)
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"

    resp = test_client.post(
        f"/leads/{lead.id}/update",
        data={
            "name": "Bobby",
            "phone": "333",
            "email": "bobby@example.com",
            "address": "",
            "company": "",
            "secondary_phone": "",
            "campaign_id": campaign.id,
            "lead_type": lead_type.name,
            "caller_name": "",
            "caller_number": "",
            "notes": "",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Bobby" in resp.data

    resp = test_client.post(
        f"/leads/{lead.id}/delete", follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"Bobby" not in resp.data


def test_leads_page_bulk_delete(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(
        id="camp1", campaign_name="Camp", client=client
    )
    lead_type = LeadType(id="lt1", name="Lead1")
    session.add_all([client, campaign, lead_type])
    session.commit()

    lead1 = app_module.Lead(
        name="Bob",
        phone="222",
        email="b@example.com",
        campaign_id=campaign.id,
        client_id=client.id,
        lead_type=lead_type.name,
    )
    lead2 = app_module.Lead(
        name="Eve",
        phone="444",
        email="e@example.com",
        campaign_id=campaign.id,
        lead_type=lead_type.name,
    )
    session.add_all([lead1, lead2])
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"

    ids = [str(lead1.id), str(lead2.id)]
    resp = test_client.post(
        "/leads/bulk-delete",
        data={"lead_ids": ids},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert session.query(app_module.Lead).count() == 0


def test_lead_types_page_displays_group_lead_types(app_module, session):
    group = LeadTypeGroup(id="g1", name="Group1")
    lead_type = LeadType(id="lt1", name="Lead1", group_id=group.id)
    session.add_all([group, lead_type])
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"
    resp = test_client.get("/lead-types")
    assert resp.status_code == 200
    assert b"Group1" in resp.data
    assert b"Lead1" in resp.data
    assert b"No lead types" not in resp.data


def test_manage_dispositions_accepts_comma_separated(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    group = LeadTypeGroup(id="g1", name="Group1")
    session.add(group)
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"

    resp = test_client.post(
        f"/lead-types/{group.id}/manage", data={"dispositions": "A, B"}
    )

    assert resp.status_code == 302
    names = [
        lt.name for lt in session.query(LeadType).filter_by(group_id=group.id)
    ]
    assert set(names) == {"A", "B"}


def test_manage_client_displays_lead_types(app_module, session):
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    group = LeadTypeGroup(id="g1", name="Group1")
    lead_type = LeadType(id="lt1", name="Lead1", group_id=group.id)
    campaign = app_module.Campaign(
        id="camp1", campaign_name="Camp", client=client
    )
    clt = CampaignLeadType(
        campaign_id=campaign.id,
        lead_type_id=lead_type.id,
        lead_type_name=lead_type.name,
    )
    session.add_all([client, group, lead_type, campaign, clt])
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"
    resp = test_client.get(f"/clients/{client.id}/manage")
    assert resp.status_code == 200
    assert b"Group1" in resp.data
    assert b"Lead1" in resp.data


def test_manage_client_handles_missing_lead_type(app_module, session):
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(
        id="camp1", campaign_name="Camp", client=client
    )
    # Create a CampaignLeadType referencing a lead type that does not exist
    clt = CampaignLeadType(
        campaign_id=campaign.id,
        lead_type_id="lt1",
        lead_type_name="Lead1",
    )
    session.add_all([client, campaign, clt])
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"
    resp = test_client.get(f"/clients/{client.id}/manage")
    assert resp.status_code == 200
    assert b"Lead1" in resp.data


def test_manage_campaign_assigns_groups(app_module, session):
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    group = LeadTypeGroup(id="g1", name="Group1")
    lead_type = LeadType(id="lt1", name="Lead1", group_id=group.id)
    campaign = app_module.Campaign(id="camp1", campaign_name="Camp")
    session.add_all([client, group, lead_type, campaign])
    session.commit()

    app_module.app.config["WTF_CSRF_ENABLED"] = False
    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"

    resp = test_client.post(
        f"/campaigns/{campaign.id}",
        data={"client_id": str(client.id), "group_ids": [group.id]},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    cltgs = (
        session.query(CampaignLeadTypeGroup)
        .filter_by(campaign_id=campaign.id)
        .all()
    )
    assert len(cltgs) == 1
    assert cltgs[0].lead_type_group_id == group.id
    session.refresh(campaign)
    assert campaign.client_id == client.id

    resp2 = test_client.get(f"/clients/{client.id}/manage")
    assert resp2.status_code == 200
    assert b"Group1" in resp2.data
    assert b"Lead1" in resp2.data


def test_manage_campaign_updates_existing_leads(app_module, session):
    """Assigning a client to a campaign updates existing leads."""

    # Create campaign without client and a lead associated with it
    campaign = app_module.Campaign(id="camp1", campaign_name="Camp")
    session.add(campaign)
    session.commit()

    assert app_module.create_lead(
        "Bob", "222", "b@example.com", campaign_id=campaign.id
    )
    lead = session.query(app_module.Lead).first()
    assert lead.client_id is None

    # Create client and assign it to the campaign through the route
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    session.add(client)
    session.commit()

    app_module.app.config["WTF_CSRF_ENABLED"] = False
    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"

    resp = test_client.post(
        f"/campaigns/{campaign.id}",
        data={"client_id": str(client.id)},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    session.expire_all()
    updated_lead = session.get(app_module.Lead, lead.id)
    assert updated_lead.client_id == client.id
    assert app_module.list_leads()[0]["client"] == "Acme"


def test_manage_campaign_changes_client_updates_leads(app_module, session):
    """Changing the campaign's client propagates to associated leads."""

    # Initial setup with campaign linked to first client
    client1 = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    client2 = app_module.Client(
        company_name="BetaCo",
        contact_name="Bob",
        contact_email="b@example.com",
        phone="222",
    )
    campaign = app_module.Campaign(
        id="camp1", campaign_name="Camp", client=client1
    )
    session.add_all([client1, client2, campaign])
    session.commit()

    # Create lead tied to campaign; client_id should mirror client1
    assert app_module.create_lead(
        "Lead1", "333", "l1@example.com", campaign_id=campaign.id
    )
    lead = session.query(app_module.Lead).first()
    assert lead.client_id == client1.id

    # Reassign campaign to client2 via the manage route
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"

    resp = test_client.post(
        f"/campaigns/{campaign.id}",
        data={"client_id": str(client2.id)},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    session.expire_all()
    updated_lead = session.get(app_module.Lead, lead.id)
    assert updated_lead.client_id == client2.id
    assert app_module.list_leads()[0]["client"] == "BetaCo"


def test_manage_client_uses_group_lead_types(app_module, session):
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    group = LeadTypeGroup(id="g1", name="Group1")
    lead_type = LeadType(id="lt1", name="Lead1", group_id=group.id)
    campaign = app_module.Campaign(
        id="camp1", campaign_name="Camp", client=client
    )
    cltg = CampaignLeadTypeGroup(
        campaign_id=campaign.id, lead_type_group_id=group.id
    )
    session.add_all([client, group, lead_type, campaign, cltg])
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"
    resp = test_client.get(f"/clients/{client.id}/manage")
    assert resp.status_code == 200
    assert b"Group1" in resp.data
    assert b"Lead1" in resp.data


def test_delete_client_route(app_module, session):
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    session.add(client)
    session.commit()
    client_id = client.id

    app_module.app.config["WTF_CSRF_ENABLED"] = False
    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"

    resp = test_client.post(
        f"/clients/{client_id}/delete", follow_redirects=True
    )
    assert resp.status_code == 200
    session.expire_all()
    session.expunge_all()
    assert session.get(app_module.Client, client_id) is None


def test_list_leads_filters(app_module, session):
    """Filtering in list_leads should respect all parameters."""
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(id="camp1", campaign_name="Camp", client=client)
    lead_type = LeadType(id="lt1", name="Lead1")
    other_type = LeadType(id="lt2", name="Other")
    session.add_all([client, campaign, lead_type, other_type])
    session.commit()

    app_module.create_lead(
        "Bob",
        "222",
        "b@example.com",
        "",
        "",
        "",
        campaign.id,
        lead_type.name,
    )
    app_module.create_lead(
        "Eve",
        "333",
        "e@example.com",
        "",
        "",
        "",
        None,
        other_type.name,
    )

    assert len(app_module.list_leads(client_id=client.id)) == 1
    assert len(app_module.list_leads(campaign_id=campaign.id)) == 1
    assert len(app_module.list_leads(lead_type=lead_type.name)) == 1
    future = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    assert app_module.list_leads(start_date=future) == []


def test_leads_report_download(app_module, session):
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(id="camp1", campaign_name="Camp", client=client)
    lead_type = LeadType(id="lt1", name="Lead1")
    session.add_all([client, campaign, lead_type])
    session.commit()
    lead = app_module.Lead(
        name="Bob",
        phone="222",
        email="b@example.com",
        campaign_id=campaign.id,
        lead_type=lead_type.name,
    )
    session.add(lead)
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"
    resp = test_client.get("/leads/report")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "text/csv"

    rows = list(csv.reader(io.StringIO(resp.data.decode("utf-8"))))
    assert rows[0] == [
        "ID",
        "Name",
        "Phone",
        "Client",
        "Campaign",
        "Lead Type",
        "Notes",
        "Created",
    ]
    assert any(row[1] == "Bob" for row in rows[1:])


def test_leads_report_selected_columns(app_module, session):
    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(id="camp1", campaign_name="Camp", client=client)
    lead_type = LeadType(id="lt1", name="Lead1")
    session.add_all([client, campaign, lead_type])
    session.commit()
    lead = app_module.Lead(
        name="Bob",
        phone="222",
        email="b@example.com",
        campaign_id=campaign.id,
        lead_type=lead_type.name,
    )
    session.add(lead)
    session.commit()

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"
    resp = test_client.get("/leads/report?columns=name&columns=phone")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "text/csv"

    rows = [row for row in csv.reader(io.StringIO(resp.data.decode("utf-8"))) if row]
    assert rows[0] == ["Name", "Phone"]
    assert rows[1] == ["Bob", "222"]


def test_create_lead_sends_notifications(app_module, session, monkeypatch):
    """Lead creation triggers client notifications when enabled."""

    client = app_module.Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = app_module.Campaign(id="camp1", campaign_name="Camp", client=client)
    lead_type = LeadType(id="lt1", name="Lead1")
    session.add_all([client, campaign, lead_type])
    session.commit()
    setting = ClientLeadTypeSetting(
        client_id=client.id,
        lead_type_id=lead_type.id,
        sms_enabled=True,
        email_enabled=True,
    )
    session.add(setting)
    session.commit()

    sms_called = {}
    email_called = {}

    def fake_sms(to, msg):
        sms_called["to"] = to
        sms_called["msg"] = msg
        return True

    def fake_email(to, subject, body, *, html=None):
        email_called["to"] = to
        email_called["subject"] = subject
        email_called["body"] = body
        email_called["html"] = html
        return True

    monkeypatch.setattr(app_module.services.lead_service, "send_sms", fake_sms)
    monkeypatch.setattr(app_module.services.lead_service, "send_email", fake_email)

    assert app_module.create_lead(
        "Bob", "222", "b@example.com", campaign_id=campaign.id, lead_type="lt1"
    )
    assert sms_called["to"] == client.phone
    assert "Bob" in sms_called["msg"] and "222" in sms_called["msg"]
    assert email_called["to"] == client.contact_email
    assert "Bob" in email_called["body"] and "222" in email_called["body"]
    assert email_called.get("html") is None
