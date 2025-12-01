"""Routes for configuring integrations and managing user permissions."""


import os

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    session as flask_session,
    abort,
)

from uuid import uuid4
from types import SimpleNamespace

from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.inspection import inspect

from ..models.lead import Lead
from ..models.client import Client

from ..models.justcall_credential import JustCallCredential
from ..models.justcall_webhook import JustCallWebhook
from ..models.gmail_credential import GmailCredential
from ..models.notification_template import NotificationTemplate
from ..models.user import User
from ..models.page_permission import PagePermission
from ..services.auth_decorators import (
    require_superuser,
    require_page,
    PAGE_OPTIONS,
)
from ..services.helpers import get_session
from ..services.auth_service import send_activation_email, create_supabase_user
from ..services.sms_service import send_sms, fetch_sms_numbers
from ..services.email_service import (
    send_email,
    verify_gmail_api_credentials,
    GmailCredentialAuthenticationError,
    GmailCredentialSendError,
    get_gmail_api_status,
)

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


def _notification_templates_supports_email_text(session) -> bool:
    """Return True if the notification_templates table has the email_text column."""

    bind = session.get_bind()
    if bind is None:
        return True
    try:
        columns = sa_inspect(bind).get_columns("notification_templates")
    except Exception:
        return False
    return any(column["name"] == "email_text" for column in columns)


def _load_legacy_notification_templates(session):
    """Load notification templates when the email_text column is unavailable."""

    rows = session.execute(
        text(
            "SELECT id, name, sms_template, email_subject, email_html, is_default "
            "FROM notification_templates ORDER BY name"
        )
    ).mappings()
    return [
        SimpleNamespace(
            id=row["id"],
            name=row["name"],
            sms_template=row.get("sms_template"),
            email_subject=row.get("email_subject"),
            email_text="",
            email_html=row.get("email_html"),
            is_default=row.get("is_default"),
        )
        for row in rows
    ]


def _load_legacy_notification_template(session, template_id: int):
    """Load a single notification template when email_text is unavailable."""

    row = (
        session.execute(
            text(
                "SELECT id, name, sms_template, email_subject, email_html, is_default "
                "FROM notification_templates WHERE id = :template_id"
            ),
            {"template_id": template_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    return SimpleNamespace(
        id=row["id"],
        name=row["name"],
        sms_template=row.get("sms_template"),
        email_subject=row.get("email_subject"),
        email_text="",
        email_html=row.get("email_html"),
        is_default=row.get("is_default"),
    )


@settings_bp.route("/justcall", methods=["GET", "POST"])
@require_superuser
@require_page
def justcall_settings():  # pragma: no cover - mostly template rendering
    """Display and manage stored JustCall API credentials and webhooks."""

    with get_session() as session:
        creds = session.query(JustCallCredential).first()
        webhooks = session.query(JustCallWebhook).all()
        numbers = fetch_sms_numbers() if creds else []
        if request.method == "POST":
            if request.form.get("delete") and creds:
                session.delete(creds)
                session.commit()
                flash("Credentials deleted", "info")
                return redirect(url_for("settings.justcall_settings"))
            elif request.form.get("add_webhook"):
                target_type = request.form.get("target_type", "lead")
                token = uuid4().hex
                session.add(JustCallWebhook(token=token, target_type=target_type))
                session.commit()
                flash("Webhook added", "info")
                return redirect(url_for("settings.justcall_settings"))
            elif request.form.get("delete_webhook"):
                webhook_id = int(request.form.get("delete_webhook", "0"))
                webhook = session.get(JustCallWebhook, webhook_id)
                if webhook:
                    session.delete(webhook)
                    session.commit()
                    flash("Webhook deleted", "info")
                return redirect(url_for("settings.justcall_settings"))
            elif request.form.get("save_number") and creds:
                creds.sms_number = request.form.get("sms_number", "")
                session.commit()
                flash("Default number saved", "info")
                return redirect(url_for("settings.justcall_settings"))
            elif not creds:
                api_key = request.form.get("api_key", "")
                api_secret = request.form.get("api_secret", "")
                session.add(
                    JustCallCredential(api_key=api_key, api_secret=api_secret)
                )
                session.commit()
                flash("Credentials saved", "info")
                return redirect(url_for("settings.justcall_settings"))
    return render_template(
        "justcall_settings.html", credentials=creds, webhooks=webhooks, numbers=numbers
    )


@settings_bp.route("/gmail", methods=["GET", "POST"])
@require_superuser
@require_page
def gmail_settings():  # pragma: no cover - mostly template rendering
    """Display and manage stored Gmail API credentials."""

    with get_session() as session:
        creds = session.query(GmailCredential).first()
        api_status = get_gmail_api_status(creds)

        if request.method == "POST":
            action = request.form.get("action", "")

            if action == "delete_api" and creds:
                creds.api_client_id = ""
                creds.api_client_secret = ""
                creds.api_refresh_token = ""
                creds.api_from_email = ""
                creds.cc_emails = ""
                creds.bcc_emails = ""
                for key in (
                    "GMAIL_API_CLIENT_ID",
                    "GMAIL_API_CLIENT_SECRET",
                    "GMAIL_API_REFRESH_TOKEN",
                    "GMAIL_API_FROM_EMAIL",
                ):
                    os.environ.pop(key, None)
                session.commit()
                flash("Gmail API credentials removed.", "info")
                return redirect(url_for("settings.gmail_settings"))

            if action == "save_api":
                client_id = request.form.get("api_client_id", "").strip()
                client_secret = request.form.get("api_client_secret", "").strip()
                refresh_token = request.form.get("api_refresh_token", "").strip()
                from_email = request.form.get("api_from_email", "").strip()
                cc_emails = ",".join(
                    e.strip()
                    for e in request.form.get("cc_emails", "").split(",")
                    if e.strip()
                )
                bcc_emails = ",".join(
                    e.strip()
                    for e in request.form.get("bcc_emails", "").split(",")
                    if e.strip()
                )

                try:
                    verify_gmail_api_credentials(
                        client_id, client_secret, refresh_token, from_email
                    )
                except GmailCredentialAuthenticationError as exc:
                    flash(str(exc) or "Unable to verify Gmail API credentials.", "danger")
                    return redirect(url_for("settings.gmail_settings"))
                except GmailCredentialSendError as exc:
                    flash(str(exc) or "Unable to verify Gmail API credentials.", "danger")
                    return redirect(url_for("settings.gmail_settings"))

                if not creds:
                    creds = GmailCredential()
                    session.add(creds)

                if not creds.username:
                    creds.username = from_email or "gmail"
                if creds.password is None or creds.password == "":
                    creds.password = creds.password or ""
                if not creds.from_email:
                    creds.from_email = from_email

                creds.api_client_id = client_id
                creds.api_client_secret = client_secret
                creds.api_refresh_token = refresh_token
                creds.api_from_email = from_email
                creds.cc_emails = cc_emails
                creds.bcc_emails = bcc_emails

                os.environ["GMAIL_API_CLIENT_ID"] = client_id
                os.environ["GMAIL_API_CLIENT_SECRET"] = client_secret
                os.environ["GMAIL_API_REFRESH_TOKEN"] = refresh_token
                if from_email:
                    os.environ["GMAIL_API_FROM_EMAIL"] = from_email

                session.commit()
                flash("Gmail API credentials saved.", "info")
                return redirect(url_for("settings.gmail_settings"))

    return render_template(
        "gmail_settings.html",
        credentials=creds,
        api_status=api_status,
    )


@settings_bp.route("/templates", methods=["GET", "POST"])
@require_superuser
@require_page
def notification_templates():  # pragma: no cover - mostly template rendering
    """Create and manage reusable notification templates."""

    with get_session() as session:
        email_text_supported = _notification_templates_supports_email_text(session)
        if email_text_supported:
            templates = (
                session.query(NotificationTemplate)
                .order_by(NotificationTemplate.name)
                .all()
            )
        else:
            templates = _load_legacy_notification_templates(session)
        if request.method == "POST":
            if not email_text_supported:
                flash(
                    "Notification templates require a database migration before they can "
                    "be modified.",
                    "danger",
                )
                return redirect(url_for("settings.notification_templates"))
            action = request.form.get("action", "add")
            if action == "add":
                name = request.form.get("name", "")
                sms_template = request.form.get("sms_template", "")
                email_subject = request.form.get("email_subject", "")
                email_text = request.form.get("email_text", "")
                email_html = request.form.get("email_html", "")
                channel = request.form.get("channel", "both")
                if channel == "sms":
                    email_subject = ""
                    email_text = ""
                    email_html = ""
                elif channel == "email":
                    sms_template = ""
                is_default = request.form.get("is_default") == "on"
                if is_default:
                    session.query(NotificationTemplate).update({"is_default": False})
                session.add(
                    NotificationTemplate(
                        name=name,
                        sms_template=sms_template,
                        email_subject=email_subject,
                        email_text=email_text,
                        email_html=email_html,
                        is_default=is_default,
                    )
                )
                session.commit()
                flash("Template saved", "info")
            elif action == "set_default":
                template_id = int(request.form.get("template_id", "0"))
                session.query(NotificationTemplate).update({"is_default": False})
                tmpl = session.get(NotificationTemplate, template_id)
                if tmpl:
                    tmpl.is_default = True
                    session.commit()
                    flash("Default template updated", "info")
            elif action == "delete":
                template_id = int(request.form.get("template_id", "0"))
                tmpl = session.get(NotificationTemplate, template_id)
                if tmpl:
                    session.delete(tmpl)
                    session.commit()
                    flash("Template deleted", "info")
            return redirect(url_for("settings.notification_templates"))

    # Build separate lists of available placeholder fields from Lead and Client models
    lead_placeholders = sorted(
        set(
            [attr.key for attr in inspect(Lead).mapper.column_attrs]
            + ["first_name", "last_name"]
        )
    )
    client_placeholders = sorted(
        set(
            [f"client_{attr.key}" for attr in inspect(Client).mapper.column_attrs]
            + ["client_first_name", "client_last_name"]
        )
    )

    return render_template(
        "notification_templates.html",
        templates=templates,
        lead_placeholders=lead_placeholders,
        client_placeholders=client_placeholders,
        email_text_supported=email_text_supported,
    )


@settings_bp.route("/templates/<int:template_id>", methods=["GET", "POST"])
@require_superuser
@require_page
def edit_notification_template(template_id: int):  # pragma: no cover - mostly template rendering
    """Edit an existing notification template."""

    with get_session() as session:
        email_text_supported = _notification_templates_supports_email_text(session)
        if email_text_supported:
            tmpl = session.get(NotificationTemplate, template_id)
        else:
            tmpl = _load_legacy_notification_template(session, template_id)
        if tmpl is None:
            abort(404)

        if request.method == "POST":
            if not email_text_supported:
                flash(
                    "Notification templates require a database migration before they can "
                    "be modified.",
                    "danger",
                )
                return redirect(url_for("settings.notification_templates"))
            name = request.form.get("name", "")
            sms_template = request.form.get("sms_template", "")
            email_subject = request.form.get("email_subject", "")
            email_text = request.form.get("email_text", "")
            email_html = request.form.get("email_html", "")
            channel = request.form.get("channel", "both")
            if channel == "sms":
                email_subject = ""
                email_text = ""
                email_html = ""
            elif channel == "email":
                sms_template = ""
            is_default = request.form.get("is_default") == "on"
            tmpl.name = name
            tmpl.sms_template = sms_template
            tmpl.email_subject = email_subject
            tmpl.email_text = email_text
            tmpl.email_html = email_html
            if is_default:
                session.query(NotificationTemplate).update({"is_default": False})
            tmpl.is_default = is_default
            session.commit()
            flash("Template updated", "info")
            return redirect(url_for("settings.notification_templates"))

        lead_placeholders = sorted(
            set(
                [attr.key for attr in inspect(Lead).mapper.column_attrs]
                + ["first_name", "last_name"]
            )
        )
        client_placeholders = sorted(
            set(
                [f"client_{attr.key}" for attr in inspect(Client).mapper.column_attrs]
                + ["client_first_name", "client_last_name"]
            )
        )

        if tmpl.sms_template and (tmpl.email_subject or tmpl.email_html):
            channel = "both"
        elif tmpl.sms_template:
            channel = "sms"
        else:
            channel = "email"

        return render_template(
            "edit_notification_template.html",
            tmpl=tmpl,
            channel=channel,
            lead_placeholders=lead_placeholders,
            client_placeholders=client_placeholders,
            email_text_supported=email_text_supported,
        )


@settings_bp.route("/notifications/test", methods=["GET", "POST"])
@require_superuser
@require_page
def notification_test():  # pragma: no cover - mostly template rendering
    """Allow sending test SMS and email messages."""
    numbers = fetch_sms_numbers()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "sms":
            to_number = request.form.get("to_number", "")
            from_number = request.form.get("from_number", "")
            message = request.form.get("message", "")
            if send_sms(to_number, message, from_number=from_number):
                flash("SMS sent", "info")
            else:
                flash("Failed to send SMS", "danger")
        elif action == "email":
            to_email = request.form.get("to_email", "")
            body = request.form.get("body", "")
            if send_email(to_email, "Test Email", body):
                flash("Email sent", "info")
            else:
                flash("Failed to send email", "danger")
        return redirect(url_for("settings.notification_test"))

    return render_template("notification_test.html", numbers=numbers)


@settings_bp.route("/justcall/<int:webhook_id>")
@require_superuser
@require_page
def justcall_webhook_detail(webhook_id: int):
    """Display details and testing tools for a specific JustCall webhook."""

    with get_session() as session:
        webhook = session.get(JustCallWebhook, webhook_id)
        if not webhook:
            abort(404)
    return render_template("justcall_webhook_detail.html", webhook=webhook)


@settings_bp.route("/users", methods=["GET", "POST"])
@require_superuser
@require_page
def user_settings():  # pragma: no cover - mostly template rendering
    """Display and manage application users."""

    with get_session() as session:
        if request.method == "POST":
            action = request.form.get("action")
            if action == "add":
                first_name = request.form.get("first_name", "")
                last_name = request.form.get("last_name", "")
                email = request.form.get("email", "")
                role = request.form.get("role", "staff")
                is_staff = role in {"staff", "admin"}
                is_superuser = role == "admin"
                pages = request.form.getlist("pages")
                user = User(
                    email=email,
                    uid=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=is_staff,
                    is_superuser=is_superuser,
                )
                session.add(user)
                session.commit()
                for path in pages:
                    session.add(PagePermission(user_id=user.id, path=path))
                session.commit()
                try:
                    create_supabase_user(email)
                    send_activation_email(email)
                except Exception:
                    pass
                flash("User added", "info")
                return redirect(url_for("settings.user_settings"))
            if action == "update":
                user_id = int(request.form.get("user_id", "0"))
                user = session.get(User, user_id)
                if user:
                    role = request.form.get("role", "staff")
                    user.is_staff = role in {"staff", "admin"}
                    user.is_superuser = role == "admin"
                    pages = request.form.getlist("pages")
                    session.query(PagePermission).filter_by(user_id=user.id).delete()
                    for path in pages:
                        session.add(PagePermission(user_id=user.id, path=path))
                    session.commit()
                    flash("Permissions updated", "info")
                return redirect(url_for("settings.user_settings"))
        users = [
            {
                "id": u.id,
                "uid": u.uid,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "is_staff": u.is_staff,
                "is_superuser": u.is_superuser,
                "permissions": [p.path for p in u.permissions],
            }
            for u in session.query(User).order_by(User.email).all()
        ]
    return render_template(
        "user_settings.html", users=users, page_options=PAGE_OPTIONS
    )


@settings_bp.route("/profile", methods=["GET", "POST"])
def profile():
    """Allow the current user to view and update their profile information."""

    user_id = flask_session.get("user_id")
    if not user_id:
        return redirect("/login")

    with get_session() as db:
        user = db.get(User, user_id)
        if not user:
            abort(404)
        if request.method == "POST":
            user.first_name = request.form.get("first_name", user.first_name)
            user.last_name = request.form.get("last_name", user.last_name)
            db.commit()
            flash("Profile updated", "info")
            return redirect(url_for("settings.profile"))
    return render_template("profile.html", user=user)
