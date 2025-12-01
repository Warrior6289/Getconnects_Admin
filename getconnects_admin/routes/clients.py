"""Client management routes."""

from flask import Blueprint, jsonify, redirect, render_template, request, flash

from collections import defaultdict

from ..forms import ClientForm
from ..services.auth_decorators import require_staff, require_page
from ..services.client_service import create_client, list_clients, delete_client as delete_client_service
from ..services.helpers import get_session
from ..models.client import Client
from ..models.campaign import Campaign
from ..models.campaign_lead_type import CampaignLeadType
from ..models.campaign_lead_type_group import CampaignLeadTypeGroup
from ..models.client_lead_type_setting import ClientLeadTypeSetting
from ..models.lead_type import LeadType
from ..models.notification_template import NotificationTemplate

clients_bp = Blueprint("clients", __name__)


@clients_bp.route("/clients", methods=["GET", "POST"])
@require_staff
@require_page
def clients_page():
    """Render the clients page and handle new client submissions."""

    form = ClientForm()
    if form.validate_on_submit():
        create_client(
            form.company_name.data,
            form.contact_name.data,
            form.contact_email.data,
            form.phone.data,
        )
        return redirect("/clients")
    return render_template("clients.html", form=form, clients=list_clients())


@clients_bp.route("/api/clients", methods=["GET"])
@require_staff
@require_page
def clients_index():
    """Return a JSON representation of all clients."""

    return jsonify(list_clients())


@clients_bp.route("/clients/<int:client_id>/manage", methods=["GET", "POST"])
@require_staff
@require_page
def manage_client(client_id):  # pragma: no cover - template rendering
    """Edit a client's details and notification preferences."""

    form = ClientForm()
    with get_session() as session:
        client = session.get(Client, client_id)
        if not client:
            flash("Client not found", "error")
            return redirect("/clients")

        # gather campaigns and associated lead types
        campaigns = session.query(Campaign).filter_by(client_id=client_id).all()
        groups = defaultdict(list)
        lead_types = []
        lead_type_ids: set[str] = set()
        for camp in campaigns:
            clts = session.query(CampaignLeadType).filter_by(campaign_id=camp.id).all()
            if clts:
                for clt in clts:
                    lt = clt.lead_type or LeadType(
                        id=clt.lead_type_id,
                        name=clt.lead_type_name,
                    )
                    if lt.id not in lead_type_ids:
                        group_name = lt.group.name if lt.group else "Ungrouped"
                        groups[group_name].append(lt)
                        lead_types.append(lt)
                        lead_type_ids.add(lt.id)
                continue

            # Fallback: derive lead types from associated groups when no
            # specific campaign lead type mappings exist. This ensures the
            # manage client page still lists available lead types for
            # campaigns that only reference lead type groups.
            for cltg in (
                session.query(CampaignLeadTypeGroup)
                .filter_by(campaign_id=camp.id)
                .all()
            ):
                group = cltg.group
                for lt in group.lead_types:
                    if lt.id not in lead_type_ids:
                        group_name = group.name if group else "Ungrouped"
                        groups[group_name].append(lt)
                        lead_types.append(lt)
                        lead_type_ids.add(lt.id)

        settings = {
            s.lead_type_id: s
            for s in session.query(ClientLeadTypeSetting)
            .filter_by(client_id=client_id)
            .all()
        }
        templates = (
            session.query(NotificationTemplate)
            .order_by(NotificationTemplate.name)
            .all()
        )

        if request.method == "POST" and form.validate_on_submit():
            client.company_name = form.company_name.data
            client.contact_name = form.contact_name.data
            client.contact_email = form.contact_email.data
            client.phone = form.phone.data

            for lt in lead_types:
                setting = settings.get(lt.id)
                if not setting:
                    setting = ClientLeadTypeSetting(
                        client_id=client_id, lead_type_id=lt.id
                    )
                    session.add(setting)
                setting.sms_enabled = request.form.get(f"sms_{lt.id}") == "on"
                setting.email_enabled = request.form.get(f"email_{lt.id}") == "on"
                setting.template_id = (
                    int(val) if (val := request.form.get(f"template_{lt.id}")) else None
                )
                setting.sms_template = ""
                setting.email_subject = ""
                setting.email_html = ""
            session.commit()
            flash("Client updated", "info")
            return redirect("/clients")

        if request.method == "GET":
            form.company_name.data = client.company_name
            form.contact_name.data = client.contact_name
            form.contact_email.data = client.contact_email
            form.phone.data = client.phone

        return render_template(
            "manage_client.html",
            form=form,
            client=client,
            groups=dict(groups),
            settings=settings,
            templates=templates,
        )


@clients_bp.route("/clients/<int:client_id>/delete", methods=["POST"])
@require_staff
@require_page
def delete_client(client_id):
    """Delete the specified client and redirect to the clients list."""

    if delete_client_service(client_id):
        flash("Client deleted", "info")
    return redirect("/clients")
