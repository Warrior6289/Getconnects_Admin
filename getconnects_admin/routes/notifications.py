"""Notification log routes."""

from flask import Blueprint, abort, jsonify, render_template, request

from ..services.helpers import get_session
from ..models.notification_log import NotificationLog

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/notifications", methods=["GET"])
def notifications_index():
    """Return recent notification logs as JSON."""
    limit = request.args.get("limit", 10, type=int)
    with get_session() as session:
        logs = (
            session.query(NotificationLog)
            .order_by(NotificationLog.id.desc())
            .limit(limit)
            .all()
        )
        data = [
            {
                "id": log.id,
                "client_id": log.client_id,
                "client_name": (
                    log.client.company_name
                    if getattr(log, "client", None)
                    else None
                ),
                "lead_id": log.lead_id,
                "lead_name": (
                    log.lead.name
                    if getattr(log, "lead", None)
                    else None
                ),
                "channel": log.channel,
                "status": log.status,
                "message": log.message,
            }
            for log in logs
        ]
    return jsonify(data)


@notifications_bp.route("/notifications/all", methods=["GET"])
def notifications_all():  # pragma: no cover - mostly template rendering
    """Render a page listing all notification logs."""
    with get_session() as session:
        logs = (
            session.query(NotificationLog)
            .order_by(NotificationLog.id.desc())
            .all()
        )
        return render_template("notifications.html", logs=logs)


@notifications_bp.route("/notifications/<int:log_id>", methods=["GET"])
def notification_detail(log_id):  # pragma: no cover - template rendering
    """Render a detail page for a single notification log."""
    with get_session() as session:
        log = session.get(NotificationLog, log_id)
        if not log:
            abort(404)
        return render_template("notification_detail.html", log=log)


__all__ = ["notifications_bp"]
