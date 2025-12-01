"""Campaign management routes."""

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from ..models.campaign import Campaign
from ..models.campaign_lead_type_group import CampaignLeadTypeGroup
from ..models.lead_type_group import LeadTypeGroup
from ..models.lead import Lead
from ..services.campaign_service import list_campaigns
from ..services.client_service import list_clients
from ..services.helpers import get_session
from ..services.justcall_service import fetch_campaigns, sync_campaigns
from ..services.auth_decorators import require_page

campaigns_bp = Blueprint("campaigns", __name__)


@campaigns_bp.route("/campaigns", methods=["GET"])
@require_page
def campaigns_page():  # pragma: no cover - template rendering
    """Render the campaigns listing page."""

    return render_template("campaigns.html")


@campaigns_bp.route("/api/campaigns", methods=["GET"])
@require_page
def campaigns_index():
    """Return a JSON representation of all campaigns."""

    return jsonify(list_campaigns())


@campaigns_bp.route("/campaigns/sync", methods=["POST"])
@require_page
def sync_campaigns_route():
    """Synchronise campaigns using stored JustCall credentials."""

    from ..models.justcall_credential import (
        JustCallCredential,
    )  # local import to avoid circular

    with get_session() as session:
        creds = session.query(JustCallCredential).first()
        if not creds:
            flash("No API credentials configured", "error")
            return redirect(url_for("campaigns.campaigns_page"))
    try:  # pragma: no cover - network errors
        campaigns = fetch_campaigns(creds.api_key, creds.api_secret)
        sync_campaigns(campaigns)
        flash("Campaigns synchronised", "info")
    except Exception as exc:  # pragma: no cover - network errors
        flash(f"Sync failed: {exc}", "error")
    return redirect(url_for("campaigns.campaigns_page"))


@campaigns_bp.route("/campaigns/<campaign_id>", methods=["GET", "POST"])
@require_page
def manage_campaign(campaign_id: str):  # pragma: no cover - template rendering
    """Assign a client and lead type groups to a campaign."""

    if request.method == "POST":
        client_id = request.form.get("client_id")
        group_ids = request.form.getlist("group_ids")
        with get_session() as session:
            campaign = session.get(Campaign, campaign_id)
            campaign.client_id = int(client_id) if client_id else None

            # Propagate client assignment to existing leads for this campaign so
            # that the leads page reflects the updated client immediately.
            session.query(Lead).filter_by(campaign_id=campaign_id).update(
                {"client_id": campaign.client_id}, synchronize_session=False
            )

            # update lead type group assignments
            session.query(CampaignLeadTypeGroup).filter_by(
                campaign_id=campaign_id
            ).delete()
            for gid in group_ids:
                if gid:
                    session.add(
                        CampaignLeadTypeGroup(
                            campaign_id=campaign_id,
                            lead_type_group_id=gid,
                        )
                    )
            session.commit()
        flash("Campaign updated", "info")
        return redirect(url_for("campaigns.campaigns_page"))

    clients = list_clients()
    with get_session() as session:
        campaign = session.get(Campaign, campaign_id)
        selected_groups = [
            g.lead_type_group_id
            for g in session.query(CampaignLeadTypeGroup).filter_by(
                campaign_id=campaign_id
            )
        ]
        groups = [
            {"id": g.id, "name": g.name}
            for g in session.query(LeadTypeGroup).all()
        ]
        data = {
            "id": campaign.id,
            "campaign_name": campaign.campaign_name,
            "client_id": campaign.client_id,
        }
    return render_template(
        "manage_campaign.html",
        campaign=data,
        clients=clients,
        groups=groups,
        selected_groups=selected_groups,
    )
