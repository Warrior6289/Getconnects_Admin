"""Application factory and module re-exports."""

from dotenv import load_dotenv
from flask import Flask, redirect, request, session, url_for, render_template
from flask_wtf import CSRFProtect
from flask_caching import Cache
import click

from .models import Base, SessionLocal, engine
from .db_bootstrap import ensure_lead_type_tables
from .models.user import User
from .models.client import Client
from .models.campaign import Campaign
from .models.lead import Lead
from .models.notification_template import NotificationTemplate
from .models.notification_log import NotificationLog
from .routes import (
    auth_bp,
    campaigns_bp,
    settings_bp,
    clients_bp,
    stats_bp,
    dashboard_bp,
    root_bp,
    pages_bp,
    webhooks_bp,
    notifications_bp,
)
from .services.auth_service import supabase_config, verify_supabase_token
from .services.client_service import create_client, list_clients
from .services.campaign_service import list_campaigns
from .services.stats_service import get_stats, get_leads_by_campaign
from .services.lead_service import create_lead, list_leads
from .config import config, ProductionConfig

csrf = CSRFProtect()
cache = Cache()


class _DB:
    """Minimal database extension placeholder."""

    def init_app(self, app: Flask) -> None:  # pragma: no cover - no-op
        pass


db = _DB()


def create_app(config_name: str | None = None) -> Flask:
    """Application factory."""

    load_dotenv()
    app = Flask(
        __name__, template_folder="../templates", static_folder="../static"
    )
    cfg_class = config.get(config_name or "development")
    if cfg_class:
        cfg = cfg_class()
        app.config.from_object(cfg)
    secret_key = app.config.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("FLASK_SECRET_KEY must be set")
    if cfg_class is ProductionConfig and not app.config.get("ENCRYPTION_KEY"):
        raise RuntimeError("ENCRYPTION_KEY must be set in production")
    app.secret_key = secret_key
    csrf.init_app(app)
    cache.init_app(app, config={"CACHE_TYPE": "simple"})
    db.init_app(app)
    ensure_lead_type_tables(engine)

    @app.context_processor
    def inject_permissions():
        """Expose ``has_permission`` to templates."""

        def has_permission(path: str) -> bool:
            if session.get("is_superuser"):
                return True
            perms = session.get("permissions") or []
            return any(path.startswith(p) or p.startswith(path) for p in perms)

        return {"has_permission": has_permission}

    PUBLIC_ENDPOINTS = {
        "auth.login_page",
        "auth.session_login",
        "auth.logout",
        "static",
    }

    @app.before_request
    def require_login():  # pragma: no cover - simple session check
        """Redirect anonymous users to the login page."""
        if (
            request.endpoint in PUBLIC_ENDPOINTS
            or request.endpoint is None
            or request.blueprint == "webhooks"
        ):
            if request.endpoint == "auth.login_page" and "uid" in session:
                return redirect(url_for("dashboard.dashboard_index"))
            return None
        if "uid" not in session:
            return redirect(url_for("auth.login_page"))

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(campaigns_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(root_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(notifications_bp)
    csrf.exempt(webhooks_bp)

    @app.errorhandler(403)
    def forbidden(_):  # pragma: no cover - template rendering
        return render_template("403.html"), 403

    @app.cli.command("create-superuser")
    @click.argument("email")
    @click.option("--uid", default=None, help="Firebase UID; defaults to email")
    @click.option(
        "--actor-email",
        default=None,
        help="Email of an existing superuser authorising this change",
    )
    def create_superuser(email: str, uid: str | None, actor_email: str | None) -> None:
        """Promote *email* to superuser and staff."""

        db = SessionLocal()
        try:
            existing = db.query(User).filter_by(is_superuser=True).first()
            if existing:
                if not actor_email:
                    raise click.ClickException("actor-email is required once a superuser exists")
                actor = db.query(User).filter_by(email=actor_email).first()
                if not actor or not actor.is_superuser:
                    raise click.ClickException("Only existing superusers may promote users")

            user = db.query(User).filter_by(email=email).first()
            if not user:
                user = User(email=email, uid=uid or email)
                db.add(user)
            user.is_staff = True
            user.is_superuser = True
            db.commit()
            click.echo(f"User {email} promoted to superuser")
        finally:
            db.close()

    return app


__all__ = [
    "create_app",
    "csrf",
    "cache",
    "create_client",
    "list_clients",
    "list_campaigns",
    "get_stats",
    "get_leads_by_campaign",
    "create_lead",
    "list_leads",
    "verify_supabase_token",
    "supabase_config",
    "SessionLocal",
    "Client",
    "Campaign",
    "Lead",
    "User",
    "NotificationTemplate",
    "NotificationLog",
    "Base",
    "engine",
    "db",
]
