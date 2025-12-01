"""Application form definitions."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, FileField, HiddenField, SelectField, StringField
from wtforms.validators import DataRequired, Email


class ClientForm(FlaskForm):
    """Form for creating or editing a client record."""

    # Basic client information fields required for account creation
    company_name = StringField("Company Name", validators=[DataRequired()])
    contact_name = StringField("Contact Name", validators=[DataRequired()])
    contact_email = StringField(
        "Contact Email", validators=[DataRequired(), Email()]
    )
    phone = StringField("Phone", validators=[DataRequired()])


class LeadForm(FlaskForm):
    """Form for adding a new lead."""

    name = StringField("Name", validators=[DataRequired()])
    phone = StringField("Phone", validators=[DataRequired()])
    address = StringField("Address")
    email = StringField("Email", validators=[Email()])
    company = StringField("Company")
    secondary_phone = StringField("Secondary Number")
    campaign_id = SelectField(
        "Campaign", validators=[DataRequired()], choices=[]
    )
    lead_type = SelectField(
        "Lead Type", validators=[DataRequired()], choices=[]
    )
    caller_name = StringField("Caller")
    caller_number = StringField("Calling Number")
    notes = StringField("Notes")


class LeadImportForm(FlaskForm):
    """Upload form for importing leads from a CSV file."""

    file = FileField("CSV File", validators=[DataRequired()])
    name_column = HiddenField("Name Column")
    phone_column = HiddenField("Phone Column")
    email_column = SelectField(
        "Email Column",
        choices=[],
        validate_choice=False,
    )
    address_column = SelectField(
        "Address Column",
        choices=[],
        validate_choice=False,
    )
    company_column = SelectField(
        "Company Column",
        choices=[],
        validate_choice=False,
    )
    secondary_phone_column = SelectField(
        "Secondary Number Column",
        choices=[],
        validate_choice=False,
    )
    campaign_id_column = SelectField(
        "Campaign Column",
        choices=[],
        validate_choice=False,
    )
    lead_type_column = SelectField(
        "Lead Type Column",
        choices=[],
        validate_choice=False,
    )
    caller_name_column = SelectField(
        "Caller Column",
        choices=[],
        validate_choice=False,
    )
    caller_number_column = SelectField(
        "Calling Number Column",
        choices=[],
        validate_choice=False,
    )
    notes_column = SelectField(
        "Notes Column",
        choices=[],
        validate_choice=False,
    )
    consent = BooleanField("Consent", validators=[DataRequired()])
