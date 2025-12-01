"""Tests for form validation."""

from getconnects_admin.forms import ClientForm, LeadForm


def test_client_form_rejects_invalid_email(app_module):
    """ClientForm should flag invalid email addresses."""

    with app_module.app.test_request_context('/'):
        form = ClientForm(
            data={
                "company_name": "Acme",
                "contact_name": "Alice",
                "contact_email": "not-an-email",
                "phone": "111",
            },
            meta={"csrf": False},
        )
        assert not form.validate()


def test_client_form_accepts_valid_email(app_module):
    """A correctly formatted email should pass validation."""

    with app_module.app.test_request_context('/'):
        form = ClientForm(
            data={
                "company_name": "Acme",
                "contact_name": "Alice",
                "contact_email": "a@example.com",
                "phone": "111",
            },
            meta={"csrf": False},
        )
        assert form.validate()


def test_lead_form_validates_email(app_module):
    """LeadForm should validate the email field."""

    with app_module.app.test_request_context('/'):
        bad = LeadForm(
            data={
                "name": "Bob",
                "phone": "123",
                "email": "bad",
                "campaign_id": "camp1",
                "lead_type": "lt1",
            },
            meta={"csrf": False},
        )
        bad.campaign_id.choices = [("camp1", "Camp1")]
        bad.lead_type.choices = [("lt1", "LT1")]
        assert not bad.validate()

        good = LeadForm(
            data={
                "name": "Bob",
                "phone": "123",
                "email": "b@example.com",
                "campaign_id": "camp1",
                "lead_type": "lt1",
            },
            meta={"csrf": False},
        )
        good.campaign_id.choices = [("camp1", "Camp1")]
        good.lead_type.choices = [("lt1", "LT1")]
        assert good.validate()
