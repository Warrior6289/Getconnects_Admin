"""Business logic for lead operations."""

import logging
import re
from flask import current_app, flash

from .sms_service import send_sms
from .email_service import send_email
from sqlalchemy.inspection import inspect

try:
    from ..models.campaign import Campaign
    from ..models.lead import Lead
    from ..models.client import Client
    from ..models.client_lead_type_setting import ClientLeadTypeSetting
    from ..models.notification_template import NotificationTemplate
    from ..models.lead_type import LeadType
    from ..models.notification_log import NotificationLog
except ImportError:  # pragma: no cover
    from models.campaign import Campaign
    from models.lead import Lead
    from models.client import Client
    from models.client_lead_type_setting import ClientLeadTypeSetting
    from models.notification_template import NotificationTemplate
    from models.lead_type import LeadType
    from models.notification_log import NotificationLog
from .helpers import get_session


def _logger():
    try:
        return current_app.logger
    except Exception:  # pragma: no cover - fallback when outside app context
        return logging.getLogger(__name__)


def _render_template(text: str, lead: Lead, client: Client | None) -> str:
    """Render *text* replacing placeholders with lead/client data."""

    if not text:
        return text
    values: dict[str, str] = {}
    # Include all lead columns
    for attr in inspect(Lead).mapper.column_attrs:
        values[attr.key] = getattr(lead, attr.key) or ""

    # Friendly name/first/last for leads
    first_name = last_name = ""
    if lead.name:
        parts = lead.name.split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
    values.update({
        "name": lead.name or "",
        "first_name": first_name,
        "last_name": last_name,
    })

    if client:
        # Include all client columns prefixed with ``client_``
        client_values = {
            f"client_{attr.key}": getattr(client, attr.key) or ""
            for attr in inspect(Client).mapper.column_attrs
        }
        client_values.update(
            {
                "client_name": client.company_name or "",
                "client_email": client.contact_email or "",
                "client_phone": client.phone or "",
            }
        )

        # Split contact name for convenience
        if client.contact_name:
            parts = client.contact_name.split(maxsplit=1)
            client_values["client_first_name"] = parts[0]
            client_values["client_last_name"] = (
                parts[1] if len(parts) > 1 else ""
            )

        values.update(client_values)

    try:
        return text.format(**values)
    except Exception:  # pragma: no cover - ignore bad templates
        return text


def _strip_html(html: str) -> str:
    """Remove HTML tags for plain-text email parts."""

    return re.sub(r"<[^>]+>", "", html)


def _query_leads(session, client_id=None, campaign_id=None, lead_type=None,
                 start_date=None, end_date=None):
    """Internal helper to build a filtered lead query."""
    query = session.query(Lead)
    if client_id:
        query = query.filter(Lead.client_id == client_id)
    if campaign_id:
        query = query.filter(Lead.campaign_id == campaign_id)
    if lead_type:
        query = query.filter(Lead.lead_type == lead_type)
    if start_date:
        query = query.filter(Lead.created_at >= start_date)
    if end_date:
        query = query.filter(Lead.created_at <= end_date)
    return query


def list_leads(
    client_id: int | None = None,
    campaign_id: str | None = None,
    lead_type: str | None = None,
    start_date=None,
    end_date=None,
) -> list[dict]:
    """Return leads as a list of dictionaries optionally filtered.

    Parameters
    ----------
    client_id, campaign_id, lead_type:
        Filter results to the specified client, campaign or lead type.
    start_date, end_date:
        ``datetime`` instances bounding the ``created_at`` timestamp.
    """

    with get_session() as session:
        query = _query_leads(
            session,
            client_id=client_id,
            campaign_id=campaign_id,
            lead_type=lead_type,
            start_date=start_date,
            end_date=end_date,
        )

        results = []
        for lead in query.all():
            results.append(
                {
                    "id": lead.id,
                    "name": lead.name,
                    "phone": lead.phone,
                    "address": lead.address,
                    "email": lead.email,
                    "company": lead.company,
                    "secondary_phone": lead.secondary_phone,
                    "client": (
                        lead.client.company_name if lead.client else "None"
                    ),
                    "campaign_id": lead.campaign_id,
                    "campaign": (
                        lead.campaign.campaign_name if lead.campaign else None
                    ),
                    "lead_type": lead.lead_type,
                    "caller_name": lead.caller_name,
                    "caller_number": lead.caller_number,
                    "notes": lead.notes,
                    "created_at": lead.created_at,
                }
            )
        return results


def list_leads_paginated(
    page: int = 1,
    per_page: int = 20,
    client_id: int | None = None,
    campaign_id: str | None = None,
    lead_type: str | None = None,
    start_date=None,
    end_date=None,
):
    """Return a slice of leads along with the total count.

    This helper is used by the HTML view to implement pagination while
    preserving the behaviour of :func:`list_leads` for other callers.
    """

    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 20

    with get_session() as session:
        query = _query_leads(
            session,
            client_id=client_id,
            campaign_id=campaign_id,
            lead_type=lead_type,
            start_date=start_date,
            end_date=end_date,
        )
        total = query.count()
        leads = (
            query.order_by(Lead.id)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        results = []
        for lead in leads:
            results.append(
                {
                    "id": lead.id,
                    "name": lead.name,
                    "phone": lead.phone,
                    "address": lead.address,
                    "email": lead.email,
                    "company": lead.company,
                    "secondary_phone": lead.secondary_phone,
                    "client": lead.client.company_name if lead.client else "None",
                    "campaign_id": lead.campaign_id,
                    "campaign": lead.campaign.campaign_name if lead.campaign else None,
                    "lead_type": lead.lead_type,
                    "caller_name": lead.caller_name,
                    "caller_number": lead.caller_number,
                    "notes": lead.notes,
                    "created_at": lead.created_at,
                }
            )

        return results, total


def create_lead(
    name: str,
    phone: str,
    email: str,
    address: str | None = None,
    company: str | None = None,
    secondary_phone: str | None = None,
    campaign_id: str | None = None,
    lead_type: str | None = None,
    caller_name: str | None = None,
    caller_number: str | None = None,
    notes: str | None = None,
    flash_error: bool = True,
) -> tuple[bool, str | None]:
    """Create a new :class:`Lead` record in the database.

    Parameters
    ----------
    flash_error:
        When ``True`` the function will emit a generic flash message on
        failure.  Bulk operations may disable this to avoid spamming the
        user with repeated messages and instead handle reporting
        themselves.
    """

    with get_session() as session:
        try:
            lead = Lead(
                name=name,
                phone=phone,
                email=email,
                address=address,
                company=company,
                secondary_phone=secondary_phone,
                campaign_id=campaign_id,
                lead_type=lead_type,
                caller_name=caller_name,
                caller_number=caller_number,
                notes=notes,
            )
            if campaign_id:
                campaign = session.get(Campaign, campaign_id)
                if campaign:
                    lead.client_id = campaign.client_id
            session.add(lead)
            session.commit()

            # Fetch client notification settings after commit and send alerts.
            try:
                client = session.get(Client, lead.client_id) if lead.client_id else None
                template = None
                sms_enabled = email_enabled = True
                if lead.client_id and lead.lead_type:
                    # ``lead.lead_type`` may contain either the lead type's
                    # identifier (preferred) or its display name from the UI.
                    # Attempt a direct lookup first and fall back to resolving
                    # by name so notifications still fire for name-based values
                    # submitted by the desktop interface.
                    setting = session.get(
                        ClientLeadTypeSetting,
                        (lead.client_id, lead.lead_type),
                    )
                    if not setting:
                        lt = (
                            session.query(LeadType)
                            .filter_by(name=lead.lead_type)
                            .first()
                        )
                        if lt:
                            setting = session.get(
                                ClientLeadTypeSetting,
                                (lead.client_id, lt.id),
                            )
                    if setting:
                        sms_enabled = setting.sms_enabled
                        email_enabled = setting.email_enabled
                        if setting.template_id:
                            template = setting.template

                if template is None:
                    template = (
                        session.query(NotificationTemplate)
                        .filter_by(is_default=True)
                        .first()
                    )

                if sms_enabled and client:
                    if not client.phone:
                        warn_msg = "Client phone missing—SMS not sent"
                        session.add(
                            NotificationLog(
                                client_id=lead.client_id,
                                lead_id=lead.id,
                                channel="sms",
                                status="skipped",
                                message=warn_msg,
                            )
                        )
                        session.commit()
                        _logger().warning(warn_msg)
                        try:
                            flash(warn_msg, "warning")
                        except Exception:  # pragma: no cover - outside request
                            _logger().debug(
                                "Unable to flash warning: no request context"
                            )
                    else:
                        if template and template.sms_template:
                            msg = _render_template(template.sms_template, lead, client)
                        else:
                            msg = f"New lead: {lead.name} {lead.phone}"
                        try:
                            if send_sms(client.phone, msg):
                                session.add(
                                    NotificationLog(
                                        client_id=lead.client_id,
                                        lead_id=lead.id,
                                        channel="sms",
                                        status="sent",
                                        message=msg,
                                    )
                                )
                                session.commit()
                                _logger().info(
                                    "SMS notification sent for lead %s", lead.id
                                )
                            else:
                                warn_msg = (
                                    f"SMS notification failed for lead {lead.id}. "
                                    "Verify JustCall credentials. [ERR_SMS_CRED]"
                                )
                                session.add(
                                    NotificationLog(
                                        client_id=lead.client_id,
                                        lead_id=lead.id,
                                        channel="sms",
                                        status="failed",
                                        message=warn_msg,
                                    )
                                )
                                session.commit()
                                _logger().warning(warn_msg)
                                try:
                                    flash(warn_msg, "warning")
                                except Exception:  # pragma: no cover - outside request
                                    _logger().debug(
                                        "Unable to flash warning: no request context"
                                    )
                        except Exception as exc:  # pragma: no cover - logging side effects
                            session.add(
                                NotificationLog(
                                    client_id=lead.client_id,
                                    lead_id=lead.id,
                                    channel="sms",
                                    status="error",
                                    message=str(exc),
                                )
                            )
                            session.commit()
                            _logger().error(
                                "Error sending SMS notification for lead %s: %s",
                                lead.id,
                                exc,
                            )

                if email_enabled and client:
                    if not client.contact_email:
                        warn_msg = "Client email missing—email not sent"
                        session.add(
                            NotificationLog(
                                client_id=lead.client_id,
                                lead_id=lead.id,
                                channel="email",
                                status="skipped",
                                message=warn_msg,
                            )
                        )
                        session.commit()
                        _logger().warning(warn_msg)
                        try:
                            flash(warn_msg, "warning")
                        except Exception:  # pragma: no cover - outside request
                            _logger().debug(
                                "Unable to flash warning: no request context"
                            )
                    else:
                        if template and template.email_subject:
                            subject = _render_template(
                                template.email_subject, lead, client
                            )
                        else:
                            subject = f"New lead: {lead.name}"
                        if template and template.email_html:
                            body_html = _render_template(
                                template.email_html, lead, client
                            )
                            body = _strip_html(body_html)
                        else:
                            body = (
                                f"Name: {lead.name}\n"
                                f"Phone: {lead.phone}\n"
                                f"Email: {lead.email}"
                            )
                            body_html = None
                        try:
                            if send_email(
                                client.contact_email,
                                subject,
                                body,
                                html=body_html,
                            ):
                                session.add(
                                    NotificationLog(
                                        client_id=lead.client_id,
                                        lead_id=lead.id,
                                        channel="email",
                                        status="sent",
                                        message=body_html or body,
                                    )
                                )
                                session.commit()
                                _logger().info(
                                    "Email notification sent for lead %s", lead.id
                                )
                            else:
                                warn_msg = (
                                    f"Email notification failed for lead {lead.id}. "
                                    "Verify Gmail credentials. [ERR_EMAIL_CRED]"
                                )
                                session.add(
                                    NotificationLog(
                                        client_id=lead.client_id,
                                        lead_id=lead.id,
                                        channel="email",
                                        status="failed",
                                        message=warn_msg,
                                    )
                                )
                                session.commit()
                                _logger().warning(warn_msg)
                                try:
                                    flash(warn_msg, "warning")
                                except Exception:  # pragma: no cover - outside request
                                    _logger().debug(
                                        "Unable to flash warning: no request context"
                                    )
                        except Exception as exc:  # pragma: no cover - logging side effects
                            session.add(
                                NotificationLog(
                                    client_id=lead.client_id,
                                    lead_id=lead.id,
                                    channel="email",
                                    status="error",
                                    message=str(exc),
                                )
                            )
                            session.commit()
                            _logger().error(
                                "Error sending email notification for lead %s: %s",
                                lead.id,
                                exc,
                            )
            except Exception as exc:  # pragma: no cover - logging side effects
                _logger().error(
                    "Notification processing failed for lead %s: %s", lead.id, exc
                )

            return True, None
        except Exception as exc:  # pragma: no cover - logging side effects
            session.rollback()
            _logger().error("Failed to create lead: %s", exc)
            if flash_error:
                flash("Failed to create lead")
            return False, str(exc)


def update_lead(
    lead_id: int,
    name: str,
    phone: str,
    email: str,
    address: str | None = None,
    company: str | None = None,
    secondary_phone: str | None = None,
    campaign_id: str | None = None,
    lead_type: str | None = None,
    caller_name: str | None = None,
    caller_number: str | None = None,
    notes: str | None = None,
) -> bool:
    """Update an existing :class:`Lead` record."""

    with get_session() as session:
        try:
            lead = session.get(Lead, lead_id)
            if not lead:
                return False
            lead.name = name
            lead.phone = phone
            lead.email = email
            lead.address = address
            lead.company = company
            lead.secondary_phone = secondary_phone
            lead.campaign_id = campaign_id
            lead.lead_type = lead_type
            lead.caller_name = caller_name
            lead.caller_number = caller_number
            lead.notes = notes
            if campaign_id:
                campaign = session.get(Campaign, campaign_id)
                if campaign:
                    lead.client_id = campaign.client_id
            session.commit()
            return True
        except Exception as exc:  # pragma: no cover - logging side effects
            session.rollback()
            _logger().error("Failed to update lead: %s", exc)
            flash("Failed to update lead")
            return False


def delete_lead(lead_id: int) -> bool:
    """Delete a lead by its identifier."""

    with get_session() as session:
        try:
            lead = session.get(Lead, lead_id)
            if not lead:
                return False
            session.delete(lead)
            session.commit()
            return True
        except Exception as exc:  # pragma: no cover - logging side effects
            session.rollback()
            _logger().error("Failed to delete lead: %s", exc)
            flash("Failed to delete lead")
            return False


def bulk_delete_leads(lead_ids: list[int]) -> int:
    """Delete multiple leads in a single transaction.

    Returns the number of deleted records.
    """

    if not lead_ids:
        return 0

    with get_session() as session:
        try:
            count = (
                session.query(Lead)
                .filter(Lead.id.in_(lead_ids))
                .delete(synchronize_session=False)
            )
            session.commit()
            return count
        except Exception as exc:  # pragma: no cover - logging side effects
            session.rollback()
            _logger().error("Failed to bulk delete leads: %s", exc)
            flash("Failed to delete leads")
            return 0
