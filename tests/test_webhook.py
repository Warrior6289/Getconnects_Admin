from models.justcall_webhook import JustCallWebhook
from models.justcall_webhook_payload import JustCallWebhookPayload
from models.lead import Lead
from models.campaign import Campaign
from models.client import Client
from sqlalchemy import text


def sample_payload():
    return [
        {
            "data": {
                "client_number": "61414270206",
                "client_name": "David Crawley",
                "caller_name": "Jackson Mittag",
                "caller_number": "61482085376",
                "disposition": "No Answer",
                "email": "dcrawley.burwood@ljh.com.au",
                "phone": "414270206",
                "custom_fields": {
                    "Company": "LJ Hooker - Burwood",
                    "Alternate Phone Number": "123",
                    "Notes": "Webhook lead note",
                },
            }
        }
    ]


def test_generate_webhook_and_receive_lead(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    client.post(
        "/settings/justcall",
        data={"target_type": "lead", "add_webhook": "1"},
        follow_redirects=True,
    )
    webhook = session.query(JustCallWebhook).first()
    assert webhook is not None
    assert len(webhook.token) == 32
    assert webhook.target_type == "lead"

    payload = sample_payload()
    public_client = app_module.app.test_client()
    resp = public_client.post(f"/webhooks/justcall/{webhook.token}", json=payload)
    assert resp.status_code == 204
    lead = session.query(Lead).first()
    assert lead.name == "David Crawley"
    assert lead.company == "LJ Hooker - Burwood"
    assert lead.notes == "Webhook lead note"
    log = session.query(JustCallWebhookPayload).filter_by(token_id=webhook.id).first()
    assert log.payload == payload
    resp = public_client.get(f"/webhooks/justcall/{webhook.token}/latest")
    assert resp.status_code == 200
    assert resp.get_json() == payload


def test_webhook_custom_mapping(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    client.post(
        "/settings/justcall",
        data={"target_type": "lead", "add_webhook": "1"},
        follow_redirects=True,
    )
    webhook = session.query(JustCallWebhook).first()

    public_client = app_module.app.test_client()
    resp = public_client.post(
        f"/webhooks/justcall/{webhook.token}/mapping",
        json={"name": "data.caller_name", "notes": "data.disposition"},
    )
    assert resp.status_code == 204

    resp = public_client.post(
        f"/webhooks/justcall/{webhook.token}", json=sample_payload()
    )
    assert resp.status_code == 204
    lead = session.query(Lead).order_by(Lead.id.desc()).first()
    assert lead.name == "Jackson Mittag"
    assert lead.notes == "No Answer"


def test_partial_mapping_retains_unmapped_fields(app_module, session):
    """Unmapped fields from payload should remain in the created object."""
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    client.post(
        "/settings/justcall",
        data={"target_type": "lead", "add_webhook": "1"},
        follow_redirects=True,
    )
    webhook = session.query(JustCallWebhook).first()

    public_client = app_module.app.test_client()
    resp = public_client.post(
        f"/webhooks/justcall/{webhook.token}/mapping",
        json={"name": "data.caller_name"},
    )
    assert resp.status_code == 204

    payload = sample_payload()
    resp = public_client.post(f"/webhooks/justcall/{webhook.token}", json=payload)
    assert resp.status_code == 204
    lead = session.query(Lead).order_by(Lead.id.desc()).first()
    assert lead.name == "Jackson Mittag"  # mapped field
    assert lead.email == payload[0]["data"]["email"]  # unmapped field retained
    assert lead.phone == payload[0]["data"]["phone"]


def test_webhook_mapping_array_index(app_module, session):
    """Mappings can reference array elements using bracket notation."""
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    client.post(
        "/settings/justcall",
        data={"target_type": "lead", "add_webhook": "1"},
        follow_redirects=True,
    )
    webhook = session.query(JustCallWebhook).first()

    public_client = app_module.app.test_client()
    resp = public_client.post(
        f"/webhooks/justcall/{webhook.token}/mapping",
        json={"name": "data.callers[1].name"},
    )
    assert resp.status_code == 204

    payload = [{"data": {"callers": [{"name": "Alice"}, {"name": "Bob"}]}}]
    resp = public_client.post(f"/webhooks/justcall/{webhook.token}", json=payload)
    assert resp.status_code == 204
    lead = session.query(Lead).order_by(Lead.id.desc()).first()
    assert lead.name == "Bob"


def test_webhook_mapping_campaign_name(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    client.post(
        "/settings/justcall",
        data={"target_type": "lead", "add_webhook": "1"},
        follow_redirects=True,
    )
    webhook = session.query(JustCallWebhook).first()

    # Existing campaign identified only by name in payload
    client = Client(
        company_name="Acme", contact_name="Ann", contact_email="a@example.com", phone="1"
    )
    session.add(client)
    session.flush()
    session.add(Campaign(id="c123", campaign_name="Campaign X", client_id=client.id))
    session.commit()

    public_client = app_module.app.test_client()
    resp = public_client.post(
        f"/webhooks/justcall/{webhook.token}/mapping",
        json={"name": "data.client_name", "campaign_name": "data.campaign_name"},
    )
    assert resp.status_code == 204

    payload = [{"data": {"client_name": "Bob", "campaign_name": "Campaign X"}}]
    resp = public_client.post(f"/webhooks/justcall/{webhook.token}", json=payload)
    assert resp.status_code == 204
    lead = session.query(Lead).order_by(Lead.id.desc()).first()
    assert lead.campaign_id == "c123"
    assert lead.client_id == client.id


def test_webhook_mapping_campaign_id_with_name(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    client.post(
        "/settings/justcall",
        data={"target_type": "lead", "add_webhook": "1"},
        follow_redirects=True,
    )
    webhook = session.query(JustCallWebhook).first()

    client_obj = Client(
        company_name="Acme",
        contact_name="Ann",
        contact_email="a@example.com",
        phone="1",
    )
    session.add(client_obj)
    session.flush()
    session.add(Campaign(id="c123", campaign_name="Campaign X", client_id=client_obj.id))
    session.commit()

    public_client = app_module.app.test_client()
    resp = public_client.post(
        f"/webhooks/justcall/{webhook.token}/mapping",
        json={"name": "data.client_name", "campaign_id": "data.campaign_name"},
    )
    assert resp.status_code == 204

    payload = [{"data": {"client_name": "Bob", "campaign_name": "Campaign X"}}]
    resp = public_client.post(f"/webhooks/justcall/{webhook.token}", json=payload)
    assert resp.status_code == 204
    lead = session.query(Lead).order_by(Lead.id.desc()).first()
    assert lead.campaign_id == "c123"
    assert lead.client_id == client_obj.id


def test_webhook_campaign_lookup_without_mapping(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    client.post(
        "/settings/justcall",
        data={"target_type": "lead", "add_webhook": "1"},
        follow_redirects=True,
    )
    webhook = session.query(JustCallWebhook).first()

    client_obj = Client(
        company_name="Acme",
        contact_name="Ann",
        contact_email="a@example.com",
        phone="1",
    )
    session.add(client_obj)
    session.flush()
    session.add(Campaign(id="c123", campaign_name="Campaign X", client_id=client_obj.id))
    session.commit()

    payload = [{"data": {"client_name": "Bob", "campaign_name": "Campaign X"}}]
    public_client = app_module.app.test_client()
    resp = public_client.post(f"/webhooks/justcall/{webhook.token}", json=payload)
    assert resp.status_code == 204
    lead = session.query(Lead).order_by(Lead.id.desc()).first()
    assert lead.campaign_id == "c123"
    assert lead.client_id == client_obj.id


def test_get_saved_mapping(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    client.post(
        "/settings/justcall",
        data={"target_type": "lead", "add_webhook": "1"},
        follow_redirects=True,
    )
    webhook = session.query(JustCallWebhook).first()
    public_client = app_module.app.test_client()
    public_client.post(
        f"/webhooks/justcall/{webhook.token}/mapping",
        json={"name": "data.caller_name"},
    )
    resp = public_client.get(f"/webhooks/justcall/{webhook.token}/mapping")
    assert resp.status_code == 200
    assert resp.get_json() == {"name": "data.caller_name"}


def test_webhook_detail_page(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    client.post(
        "/settings/justcall",
        data={"target_type": "lead", "add_webhook": "1"},
        follow_redirects=True,
    )
    webhook = session.query(JustCallWebhook).first()
    resp = client.get(f"/settings/justcall/{webhook.id}")
    assert resp.status_code == 200
    assert webhook.token.encode() in resp.data
    assert b"Notes" in resp.data


def test_campaign_webhook_with_mapping(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
        sess["is_superuser"] = True
    client.post(
        "/settings/justcall",
        data={"target_type": "campaign", "add_webhook": "1"},
        follow_redirects=True,
    )
    webhook = session.query(JustCallWebhook).first()

    public_client = app_module.app.test_client()
    resp = public_client.post(
        f"/webhooks/justcall/{webhook.token}/mapping",
        json={"id": "data.id", "campaign_name": "data.campaign_name"},
    )
    assert resp.status_code == 204

    payload = [{"data": {"id": "camp1", "campaign_name": "Camp"}}]
    resp = public_client.post(f"/webhooks/justcall/{webhook.token}", json=payload)
    assert resp.status_code == 204
    campaign = session.query(Campaign).first()
    assert campaign.campaign_name == "Camp"
    assert campaign.id != "camp1"


def test_webhook_ignores_disallowed_fields(app_module, session):
    """Fields like id or created_at should be ignored when mapping."""
    webhook = JustCallWebhook(
        token="ignore-token",
        target_type="lead",
        mapping={
            "id": "data.client_number",
            "created_at": "data.disposition",
            "name": "data.client_name",
        },
    )
    session.add(webhook)
    session.commit()

    payload = sample_payload()
    payload[0]["data"]["disposition"] = "2020-01-01T00:00:00"
    client = app_module.app.test_client()
    resp = client.post(f"/webhooks/justcall/{webhook.token}", json=payload)
    assert resp.status_code == 204
    lead = session.query(Lead).order_by(Lead.id.desc()).first()
    assert lead.name == "David Crawley"
    assert lead.id != int(payload[0]["data"]["client_number"])  # id ignored
    assert lead.created_at.isoformat() != "2020-01-01T00:00:00"


def test_justcall_webhook_accepts_list_payload(app_module, session):
    webhook = JustCallWebhook(token="list-token", target_type="lead")
    session.add(webhook)
    session.commit()

    client = app_module.app.test_client()
    payload = sample_payload()
    resp = client.post(f"/webhooks/justcall/{webhook.token}", json=payload)
    assert resp.status_code == 204
    lead = session.query(Lead).first()
    assert lead.name == "David Crawley"
    log = session.query(JustCallWebhookPayload).first()
    assert log.payload == payload


def test_justcall_webhook_accepts_single_payload(app_module, session):
    webhook = JustCallWebhook(token="single-token", target_type="lead")
    session.add(webhook)
    session.commit()

    client = app_module.app.test_client()
    payload_obj = sample_payload()[0]
    resp = client.post(f"/webhooks/justcall/{webhook.token}", json=payload_obj)
    assert resp.status_code == 204
    lead = session.query(Lead).first()
    assert lead.name == "David Crawley"
    log = session.query(JustCallWebhookPayload).first()
    assert log.payload == [payload_obj]


def test_justcall_webhook_deduplicates_identical_payload(app_module, session):
    webhook = JustCallWebhook(token="dup-token", target_type="lead")
    session.add(webhook)
    session.commit()

    client = app_module.app.test_client()
    payload = sample_payload()
    resp = client.post(f"/webhooks/justcall/{webhook.token}", json=payload)
    assert resp.status_code == 204

    duplicate_resp = client.post(f"/webhooks/justcall/{webhook.token}", json=payload)
    assert duplicate_resp.status_code == 204

    session.expire_all()
    assert session.query(Lead).count() == 1
    assert session.query(JustCallWebhookPayload).count() == 1


def test_justcall_webhook_rejects_invalid_payload(app_module, session):
    webhook = JustCallWebhook(token="bad-token", target_type="lead")
    session.add(webhook)
    session.commit()

    client = app_module.app.test_client()
    resp = client.post(
        f"/webhooks/justcall/{webhook.token}", json="not a list or object"
    )
    assert resp.status_code == 400


def test_webhook_invalid_campaign_identifier_returns_error(app_module, session):
    # Enable foreign key enforcement for SQLite so invalid campaign IDs trigger errors
    session.execute(text("PRAGMA foreign_keys=ON"))
    webhook = JustCallWebhook(token="invalid-camp", target_type="lead")
    session.add(webhook)
    session.commit()

    client = app_module.app.test_client()
    payload = [
        {
            "data": {
                "client_name": "Bob",
                "campaign_id": "nonexistent",
            }
        }
    ]
    resp = client.post(f"/webhooks/justcall/{webhook.token}", json=payload)
    assert resp.status_code in (400, 409)
    body = resp.get_json()
    assert "error" in body
    assert session.query(Lead).count() == 0
