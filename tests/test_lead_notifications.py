import pytest
from unittest.mock import MagicMock
from models.lead_type import LeadType
from models.client_lead_type_setting import ClientLeadTypeSetting
from models.notification_template import NotificationTemplate


@pytest.mark.parametrize(
    "sms_enabled,email_enabled,expected_sms_calls,expected_email_calls",
    [
        (True, True, 1, 1),
        (True, False, 1, 0),
        (False, True, 0, 1),
        (False, False, 0, 0),
    ],
)
def test_lead_notifications(app_module, session, monkeypatch,
                            sms_enabled, email_enabled,
                            expected_sms_calls, expected_email_calls):
    """Notifications respect client settings for SMS and email."""
    Client = app_module.Client
    Campaign = app_module.Campaign

    client = Client(
        company_name="Acme",
        contact_name="Alice Smith",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = Campaign(id="camp1", campaign_name="Camp", client=client)
    lead_type = LeadType(id="lt1", name="Lead1")
    session.add_all([client, campaign, lead_type])
    session.commit()

    setting = ClientLeadTypeSetting(
        client_id=client.id,
        lead_type_id=lead_type.id,
        sms_enabled=sms_enabled,
        email_enabled=email_enabled,
    )
    session.add(setting)
    session.commit()

    sms_mock = MagicMock(return_value=True)
    email_mock = MagicMock(return_value=True)
    monkeypatch.setattr(app_module.services.lead_service, "send_sms", sms_mock)
    monkeypatch.setattr(app_module.services.lead_service, "send_email", email_mock)

    assert app_module.create_lead(
        "Bob", "222", "b@example.com",
        campaign_id=campaign.id,
        lead_type=lead_type.id,
    )

    assert sms_mock.call_count == expected_sms_calls
    assert email_mock.call_count == expected_email_calls


def test_lead_notifications_template(app_module, session, monkeypatch):
    """Selected templates render fields into notifications."""

    Client = app_module.Client
    Campaign = app_module.Campaign

    client = Client(
        company_name="Acme",
        contact_name="Alice Smith",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = Campaign(id="camp1", campaign_name="Camp", client=client)
    lead_type = LeadType(id="lt1", name="Lead1")
    template = NotificationTemplate(
        name="tmpl",
        sms_template="Hi {first_name} {secondary_phone}",
        email_subject="Hello {client_first_name}",
        email_html="Contact {client_contact_name} Last {last_name}",
        is_default=False,
    )
    session.add_all([client, campaign, lead_type, template])
    session.commit()

    setting = ClientLeadTypeSetting(
        client_id=client.id,
        lead_type_id=lead_type.id,
        sms_enabled=True,
        email_enabled=True,
        template_id=template.id,
    )
    session.add(setting)
    session.commit()

    sms_mock = MagicMock(return_value=True)
    email_mock = MagicMock(return_value=True)
    monkeypatch.setattr(app_module.services.lead_service, "send_sms", sms_mock)
    monkeypatch.setattr(app_module.services.lead_service, "send_email", email_mock)

    app_module.create_lead(
        "Bob Smith", "222", "b@example.com",
        campaign_id=campaign.id,
        lead_type=lead_type.id,
        secondary_phone="333",
    )

    sms_args = sms_mock.call_args[0]
    email_args = email_mock.call_args[0]
    email_kwargs = email_mock.call_args.kwargs
    assert "Bob" in sms_args[1]
    assert "333" in sms_args[1]
    assert "Alice" in email_args[1]
    assert "Alice Smith" in email_args[2]
    assert "Smith" in email_args[2]
    assert "Alice Smith" in email_kwargs.get("html", "")


def test_lead_notifications_template_notes_per_lead(app_module, session, monkeypatch):
    """Templates render notes for each specific lead."""

    Client = app_module.Client
    Campaign = app_module.Campaign

    client = Client(
        company_name="Acme",
        contact_name="Alice Smith",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = Campaign(id="camp1", campaign_name="Camp", client=client)
    lead_type = LeadType(id="lt1", name="Lead1")
    template = NotificationTemplate(
        name="tmpl",
        sms_template="{notes}",
        email_subject="{notes}",
        email_html="{notes}",
        is_default=False,
    )
    session.add_all([client, campaign, lead_type, template])
    session.commit()

    setting = ClientLeadTypeSetting(
        client_id=client.id,
        lead_type_id=lead_type.id,
        sms_enabled=True,
        email_enabled=True,
        template_id=template.id,
    )
    session.add(setting)
    session.commit()

    sms_mock = MagicMock(return_value=True)
    email_mock = MagicMock(return_value=True)
    monkeypatch.setattr(app_module.services.lead_service, "send_sms", sms_mock)
    monkeypatch.setattr(app_module.services.lead_service, "send_email", email_mock)

    app_module.create_lead(
        "Bob",
        "111",
        "b@example.com",
        campaign_id=campaign.id,
        lead_type=lead_type.id,
        notes="Note1",
    )
    app_module.create_lead(
        "Sue",
        "222",
        "s@example.com",
        campaign_id=campaign.id,
        lead_type=lead_type.id,
        notes="Note2",
    )

    sms_msgs = [call.args[1] for call in sms_mock.call_args_list]
    email_subjects = [call.args[1] for call in email_mock.call_args_list]
    email_bodies = [call.args[2] for call in email_mock.call_args_list]
    email_html = [call.kwargs.get("html") for call in email_mock.call_args_list]
    assert sms_msgs == ["Note1", "Note2"]
    assert email_subjects == ["Note1", "Note2"]
    assert email_bodies == ["Note1", "Note2"]
    assert email_html == ["Note1", "Note2"]


def test_lead_notifications_accept_name(app_module, session, monkeypatch):
    """Notifications trigger when lead_type is provided by name."""

    Client = app_module.Client
    Campaign = app_module.Campaign

    client = Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = Campaign(id="camp1", campaign_name="Camp", client=client)
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

    sms_mock = MagicMock(return_value=True)
    email_mock = MagicMock(return_value=True)
    monkeypatch.setattr(app_module.services.lead_service, "send_sms", sms_mock)
    monkeypatch.setattr(app_module.services.lead_service, "send_email", email_mock)

    assert app_module.create_lead(
        "Bob", "222", "b@example.com",
        campaign_id=campaign.id,
        lead_type=lead_type.name,
    )

    assert sms_mock.call_count == 1
    assert email_mock.call_count == 1


def test_lead_notifications_default_when_no_setting(app_module, session, monkeypatch):
    """Notifications are sent by default when no client settings exist."""

    Client = app_module.Client
    Campaign = app_module.Campaign

    client = Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = Campaign(id="camp1", campaign_name="Camp", client=client)
    lead_type = LeadType(id="lt1", name="Lead1")
    session.add_all([client, campaign, lead_type])
    session.commit()

    sms_mock = MagicMock(return_value=True)
    email_mock = MagicMock(return_value=True)
    monkeypatch.setattr(app_module.services.lead_service, "send_sms", sms_mock)
    monkeypatch.setattr(app_module.services.lead_service, "send_email", email_mock)

    assert app_module.create_lead(
        "Bob",
        "222",
        "b@example.com",
        campaign_id=campaign.id,
        lead_type=lead_type.id,
    )

    assert sms_mock.call_count == 1
    assert email_mock.call_count == 1
