from unittest.mock import MagicMock


def test_notification_log_records_and_api(app_module, session, monkeypatch):
    Client = app_module.Client
    Campaign = app_module.Campaign
    NotificationLog = app_module.NotificationLog

    client = Client(
        company_name="Acme",
        contact_name="Alice",
        contact_email="a@example.com",
        phone="111",
    )
    campaign = Campaign(id="camp1", campaign_name="Camp", client=client)
    session.add_all([client, campaign])
    session.commit()

    sms_mock = MagicMock(return_value=True)
    email_mock = MagicMock(return_value=False)
    monkeypatch.setattr(
        app_module.services.lead_service, "send_sms", sms_mock
    )
    monkeypatch.setattr(
        app_module.services.lead_service, "send_email", email_mock
    )

    app_module.create_lead(
        "Bob", "222", "b@example.com", campaign_id=campaign.id
    )

    logs = session.query(NotificationLog).all()
    assert len(logs) == 2
    statuses = {log.channel: log.status for log in logs}
    assert statuses.get("sms") == "sent"
    assert statuses.get("email") == "failed"

    test_client = app_module.app.test_client()
    resp = test_client.get("/notifications")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    for entry in data:
        assert entry["client_name"] == "Acme"
        assert entry["lead_name"] == "Bob"
