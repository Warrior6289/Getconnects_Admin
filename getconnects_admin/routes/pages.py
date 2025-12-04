"""Miscellaneous page routes."""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    abort,
    flash,
    current_app,
    make_response,
    jsonify,
)

from ..models.campaign import Campaign
from ..models.client import Client
from ..models.lead_type_group import LeadTypeGroup
from ..models.lead_type import LeadType
from ..models.campaign_lead_type import CampaignLeadType
from ..models.campaign_lead_type_group import CampaignLeadTypeGroup
from ..services.helpers import get_session
from uuid import uuid4
from ..forms import LeadForm, LeadImportForm
from datetime import datetime
from ..services.lead_service import (
    bulk_delete_leads,
    create_lead,
    delete_lead,
    list_leads,
    list_leads_paginated,
    update_lead,
)
from ..services.client_service import list_clients
from ..services.campaign_service import list_campaigns
import csv
import io
import re
from ..services.auth_decorators import require_page

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/lead-types")
@require_page
def lead_types_page():
    """Display all lead types grouped by their category."""

    with get_session() as session:
        groups = session.query(LeadTypeGroup).all()
        group_options = [
            {
                "id": g.id,
                "name": g.name,
                "lead_types": [
                    {"id": lt.id, "name": lt.name} for lt in g.lead_types
                ],
            }
            for g in groups
        ]

    return render_template("lead_types.html", groups=group_options)


@pages_bp.route("/lead-types/<group_id>/manage", methods=["GET", "POST"])
@require_page
def manage_dispositions(group_id: str):
    with get_session() as session:
        group = session.query(LeadTypeGroup).get(group_id)
        if not group:
            abort(404)

        if request.method == "POST":
            delete_id = request.form.get("delete_id")
            if delete_id:
                lt = session.query(LeadType).get(delete_id)
                if lt and lt.group_id == group.id:
                    session.delete(lt)
                    session.commit()
                return redirect(
                    url_for("pages.manage_dispositions", group_id=group.id)
                )

            raw_disps = request.form.getlist("dispositions")
            names: list[str] = []
            for raw in raw_disps:
                parts = [p.strip() for p in raw.split(",") if p.strip()]
                names.extend(parts)

            for name in names:
                lt = LeadType(id=str(uuid4()), name=name, group_id=group.id)
                session.add(lt)
            session.commit()
            return redirect(
                url_for("pages.manage_dispositions", group_id=group.id)
            )

        data = {
            "id": group.id,
            "name": group.name,
            "lead_types": [
                {"id": lt.id, "name": lt.name}
                for lt in group.lead_types
            ],
        }
    return render_template("manage_dispositions.html", group=data)


@pages_bp.route("/leads", methods=["GET", "POST"])
@require_page
def leads_page():
    """Display existing leads and allow adding new ones."""

    # Collect filter parameters from the query string
    filter_args = {
        "client_id": request.args.get("client_id", ""),
        "campaign_id": request.args.get("campaign_id", ""),
        "lead_type": request.args.get("lead_type", ""),
        "start_date": request.args.get("start_date", ""),
        "end_date": request.args.get("end_date", ""),
    }

    # Current page for pagination
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    per_page = 20

    form = LeadForm()
    edit_form = LeadForm()
    upload_form = LeadImportForm()
    with get_session() as session:
        campaigns = session.query(Campaign).all()
        lead_types = session.query(LeadType).all()
        clients = session.query(Client).all()
        for f in (form, edit_form):
            f.campaign_id.choices = [
                (c.id, c.campaign_name) for c in campaigns
            ]
            f.lead_type.choices = [
                (lt.name, lt.name) for lt in lead_types
            ]

        type_map: dict[str, list[str]] = {}
        for clt in session.query(CampaignLeadType).all():
            name = clt.lead_type_name or (
                clt.lead_type.name if clt.lead_type else None
            )
            if name:
                type_map.setdefault(clt.campaign_id, []).append(name)

        for cltg in session.query(CampaignLeadTypeGroup).all():
            if cltg.group:
                existing = type_map.setdefault(cltg.campaign_id, [])
                for lt in cltg.group.lead_types:
                    if lt.name not in existing:
                        existing.append(lt.name)

        campaign_data = [
            {
                "id": c.id,
                "name": c.campaign_name,
                "client": c.client.company_name if c.client else "None",
                "client_id": c.client_id,
                "lead_types": type_map.get(c.id, []),
            }
            for c in campaigns
        ]
        client_data = [
            {"id": cl.id, "name": cl.company_name} for cl in clients
        ]
        all_lead_types = [lt.name for lt in lead_types]

    if form.validate_on_submit():
        create_lead(
            form.name.data,
            form.phone.data,
            form.email.data,
            form.address.data,
            form.company.data,
            form.secondary_phone.data,
            form.campaign_id.data,
            form.lead_type.data,
            form.caller_name.data,
            form.caller_number.data,
            form.notes.data,
        )
        return redirect(url_for("pages.leads_page"))

    start = (
        datetime.fromisoformat(filter_args["start_date"])
        if filter_args["start_date"]
        else None
    )
    end = (
        datetime.fromisoformat(filter_args["end_date"])
        if filter_args["end_date"]
        else None
    )
    leads, total = list_leads_paginated(
        page=page,
        per_page=per_page,
        client_id=int(filter_args["client_id"]) if filter_args["client_id"] else None,
        campaign_id=filter_args["campaign_id"] or None,
        lead_type=filter_args["lead_type"] or None,
        start_date=start,
        end_date=end,
    )
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "leads.html",
        form=form,
        edit_form=edit_form,
        upload_form=upload_form,
        leads=leads,
        campaigns=campaign_data,
        clients=client_data,
        lead_types=all_lead_types,
        filters=filter_args,
        page=page,
        total_pages=total_pages,
    )


@pages_bp.route("/leads/<int:lead_id>/update", methods=["POST"])
@require_page
def update_lead_route(lead_id: int):
    """Handle updates to an existing lead."""

    form = LeadForm()
    with get_session() as session:
        campaigns = session.query(Campaign).all()
        lead_types = session.query(LeadType).all()
        form.campaign_id.choices = [(c.id, c.campaign_name) for c in campaigns]
        form.lead_type.choices = [(lt.name, lt.name) for lt in lead_types]
    if form.validate_on_submit():
        update_lead(
            lead_id,
            form.name.data,
            form.phone.data,
            form.email.data,
            form.address.data,
            form.company.data,
            form.secondary_phone.data,
            form.campaign_id.data,
            form.lead_type.data,
            form.caller_name.data,
            form.caller_number.data,
            form.notes.data,
        )
    return redirect(url_for("pages.leads_page"))


@pages_bp.route("/leads/<int:lead_id>/delete", methods=["POST"])
@require_page
def delete_lead_route(lead_id: int):
    """Delete a single lead."""

    delete_lead(lead_id)
    return redirect(url_for("pages.leads_page"))


@pages_bp.route(
    "/leads/bulk-delete", methods=["POST"], endpoint="bulk_delete_leads"
)
@require_page
def bulk_delete_leads_route():
    """Delete multiple leads selected on the listing page."""

    ids = [int(i) for i in request.form.getlist("lead_ids")]
    bulk_delete_leads(ids)
    return redirect(url_for("pages.leads_page"))


@pages_bp.route("/leads/import", methods=["POST"])
@require_page
def import_leads():
    """Handle CSV uploads for bulk lead import."""

    form = LeadImportForm()
    if not form.validate_on_submit():
        flash("Invalid import form")
        return redirect(url_for("pages.leads_page"))

    if not form.consent.data:
        flash("Consent required to import leads")
        return redirect(url_for("pages.leads_page"))

    file = form.file.data
    mapping = {
        "name": form.name_column.data,
        "phone": form.phone_column.data,
        "email": form.email_column.data,
        "address": form.address_column.data,
        "company": form.company_column.data,
        "secondary_phone": form.secondary_phone_column.data,
        "campaign_id": form.campaign_id_column.data,
        "lead_type": form.lead_type_column.data,
        "caller_name": form.caller_name_column.data,
        "caller_number": form.caller_number_column.data,
        "notes": form.notes_column.data,
    }
    try:
        stream = io.StringIO(file.stream.read().decode("utf-8"))
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames or []

        def _norm(value: str) -> str:
            return re.sub(r"[^a-z0-9]", "", value.lower())

        lookup = {_norm(name): name for name in fieldnames}
        aliases = {
            "name": ["name", "client", "client name"],
            "phone": ["phone", "phone number", "client number"],
            "email": ["email", "email address"],
            "address": ["address"],
            "company": ["company"],
            "secondary_phone": [
                "secondary phone",
                "secondary number",
                "alternate phone number",
            ],
            "campaign_id": ["campaign", "campaign id", "campaign name"],
            "lead_type": ["lead type", "disposition", "disposition code"],
            "caller_name": ["caller", "caller name", "teammate"],
            "caller_number": [
                "calling number",
                "caller number",
                "justcall number",
            ],
            "notes": ["notes", "note"],
        }
        for key, names in aliases.items():
            if not mapping.get(key):
                for alias in names:
                    alias_key = _norm(alias)
                    if alias_key in lookup:
                        mapping[key] = lookup[alias_key]
                        break
        # Build a lookup of allowed lead types for each campaign
        with get_session() as session:
            type_map: dict[str, set[str]] = {}
            for clt in session.query(CampaignLeadType).all():
                name = clt.lead_type_name or (
                    clt.lead_type.name if clt.lead_type else None
                )
                if name:
                    type_map.setdefault(clt.campaign_id, set()).add(name)
            for cltg in session.query(CampaignLeadTypeGroup).all():
                if cltg.group:
                    existing = type_map.setdefault(cltg.campaign_id, set())
                    for lt in cltg.group.lead_types:
                        existing.add(lt.name)
        total = 0
        successes = 0
        failures: list[tuple[int, str]] = []
        for row_num, row in enumerate(reader, start=1):
            total += 1
            name_val = (
                row.get(mapping["name"], "") if mapping["name"] else ""
            )
            if not name_val:
                failures.append((row_num, "Missing name"))
                continue
            phone_val = (
                row.get(mapping["phone"], "") if mapping["phone"] else ""
            )
            if not phone_val:
                failures.append((row_num, "Missing phone"))
                continue
            campaign_value = (
                row.get(mapping["campaign_id"])
                if mapping["campaign_id"]
                else None
            )
            campaign_id: str | None = None
            if campaign_value:
                with get_session() as session:
                    campaign = session.get(Campaign, campaign_value)
                    if not campaign:
                        campaign = (
                            session.query(Campaign)
                            .filter_by(campaign_name=campaign_value)
                            .first()
                        )
                    if campaign:
                        campaign_id = campaign.id
                    else:
                        failures.append(
                            (row_num, f"Unknown campaign '{campaign_value}'")
                        )
                        continue
            lead_type_val = (
                row.get(mapping["lead_type"]) if mapping["lead_type"] else None
            )
            if lead_type_val:
                if not campaign_id:
                    failures.append(
                        (row_num, "Lead type provided without campaign")
                    )
                    continue
                allowed = type_map.get(campaign_id, set())
                if lead_type_val not in allowed:
                    failures.append(
                        (row_num, f"Unknown lead type '{lead_type_val}'")
                    )
                    continue
            caller_name_val = (
                row.get(mapping["caller_name"])
                if mapping["caller_name"]
                else None
            )
            caller_number_val = (
                row.get(mapping["caller_number"])
                if mapping["caller_number"]
                else None
            )
            ok, err = create_lead(
                name_val,
                phone_val,
                row.get(mapping["email"]) if mapping["email"] else None,
                row.get(mapping["address"]) if mapping["address"] else None,
                row.get(mapping["company"]) if mapping["company"] else None,
                row.get(mapping["secondary_phone"])
                if mapping["secondary_phone"]
                else None,
                campaign_id,
                lead_type_val,
                caller_name_val,
                caller_number_val,
                row.get(mapping["notes"]) if mapping["notes"] else None,
                flash_error=False,
            )
            if ok:
                successes += 1
            else:
                failures.append((row_num, err or "Unknown error"))
        flash(f"Imported {successes} of {total} leads")
        if failures:
            details = "; ".join(
                [f"Row {n}: {reason}" for n, reason in failures]
            )
            flash(f"Failed to import - {details}")
    except Exception as exc:
        current_app.logger.error("Failed to import leads: %s", exc)
        flash("Failed to import leads")

    return redirect(url_for("pages.leads_page"))


@pages_bp.route("/leads/report/options")
@require_page
def report_options():
    """Display a form to select columns for the leads report."""

    filters = {
        "client_id": request.args.get("client_id", ""),
        "campaign_id": request.args.get("campaign_id", ""),
        "lead_type": request.args.get("lead_type", ""),
        "start_date": request.args.get("start_date", ""),
        "end_date": request.args.get("end_date", ""),
    }
    columns = [
        ("id", "ID"),
        ("name", "Name"),
        ("phone", "Phone"),
        ("client", "Client"),
        ("campaign", "Campaign"),
        ("lead_type", "Lead Type"),
        ("notes", "Notes"),
        ("created_at", "Created"),
    ]
    return render_template("report_options.html", columns=columns, filters=filters)


@pages_bp.route("/leads/report")
@require_page
def leads_report():
    """Generate a CSV report of leads matching current filters."""
    args = {
        "client_id": request.args.get("client_id", ""),
        "campaign_id": request.args.get("campaign_id", ""),
        "lead_type": request.args.get("lead_type", ""),
        "start_date": request.args.get("start_date", ""),
        "end_date": request.args.get("end_date", ""),
    }
    start = datetime.fromisoformat(args["start_date"]) if args["start_date"] else None
    end = datetime.fromisoformat(args["end_date"]) if args["end_date"] else None
    leads = list_leads(
        client_id=int(args["client_id"]) if args["client_id"] else None,
        campaign_id=args["campaign_id"] or None,
        lead_type=args["lead_type"] or None,
        start_date=start,
        end_date=end,
    )

    # Available columns: key, display label
    default_columns = [
        ("id", "ID"),
        ("name", "Name"),
        ("phone", "Phone"),
        ("client", "Client"),
        ("campaign", "Campaign"),
        ("lead_type", "Lead Type"),
        ("notes", "Notes"),
        ("created_at", "Created"),
    ]

    selected = request.args.getlist("columns")
    if selected:
        keys = set(selected)
        columns = [c for c in default_columns if c[0] in keys]
    else:
        columns = default_columns

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([header for _, header in columns])
    for lead in leads:
        row = []
        for key, _ in columns:
            value = lead.get(key)
            if key == "created_at" and value:
                value = value.strftime("%Y-%m-%d")
            row.append(value if value is not None else "")
        writer.writerow(row)

    csv_bytes = output.getvalue().encode("utf-8")

    response = make_response(csv_bytes)
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = "attachment; filename=leads_report.csv"
    return response


@pages_bp.route("/api/search", methods=["GET"])
@require_page
def search():
    """Search across clients, campaigns, and leads."""
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify({"results": []})
    
    results = []
    query_lower = query.lower()
    
    # Search clients
    clients = list_clients()
    for client in clients:
        if (query_lower in client.get("company_name", "").lower() or
            query_lower in client.get("contact_name", "").lower() or
            query_lower in client.get("contact_email", "").lower() or
            query_lower in client.get("phone", "").lower()):
            results.append({
                "type": "client",
                "id": client["id"],
                "title": client["company_name"],
                "subtitle": f"{client.get('contact_name', '')} - {client.get('contact_email', '')}",
                "url": f"/clients/{client['id']}/manage"
            })
    
    # Search campaigns
    campaigns = list_campaigns()
    for campaign in campaigns:
        if (query_lower in campaign.get("campaign_name", "").lower() or
            query_lower in (campaign.get("client_name", "") or "").lower()):
            results.append({
                "type": "campaign",
                "id": campaign["id"],
                "title": campaign["campaign_name"],
                "subtitle": f"Client: {campaign.get('client_name', 'N/A')}",
                "url": f"/campaigns/{campaign['id']}/manage"
            })
    
    # Search leads
    leads = list_leads()
    for lead in leads:
        if (query_lower in (lead.get("name", "") or "").lower() or
            query_lower in (lead.get("email", "") or "").lower() or
            query_lower in (lead.get("phone", "") or "").lower() or
            query_lower in (lead.get("company", "") or "").lower()):
            results.append({
                "type": "lead",
                "id": lead["id"],
                "title": lead.get("name", "Unnamed Lead"),
                "subtitle": f"{lead.get('email', '')} - {lead.get('phone', '')}",
                "url": f"/leads"
            })
    
    # Limit results to 10
    return jsonify({"results": results[:10]})


@pages_bp.route("/settings/justcall")
@require_page
def settings_page():
    return render_template("placeholder.html", title="Settings")
