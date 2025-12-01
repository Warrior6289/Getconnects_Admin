"""Blueprint route registrations."""

from flask import Blueprint, redirect

from .auth import auth_bp
from .clients import clients_bp
from .campaigns import campaigns_bp
from .stats import stats_bp
from .dashboard import dashboard_bp
from .pages import pages_bp
from .settings import settings_bp
from .webhooks import webhooks_bp
from .notifications import notifications_bp

root_bp = Blueprint("root", __name__)


@root_bp.route("/")
def root_redirect():  # pragma: no cover - simple redirect
    return redirect("/dashboard")


__all__ = [
    "auth_bp",
    "clients_bp",
    "campaigns_bp",
    "stats_bp",
    "dashboard_bp",
    "pages_bp",
    "settings_bp",
    "webhooks_bp",
    "notifications_bp",
    "root_bp",
]
