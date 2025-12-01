"""Dashboard page routes."""

from flask import Blueprint, render_template

from ..services.client_service import list_clients
from ..services.stats_service import get_stats
from ..services.auth_decorators import require_page


dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
@require_page
def dashboard_index():  # pragma: no cover - view logic
    """Render the dashboard page with statistics and clients."""
    return render_template(
        "dashboard.html",
        clients=list_clients(),
        stats=get_stats(),
    )
