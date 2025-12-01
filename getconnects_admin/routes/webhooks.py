"""Webhook endpoints for third-party integrations."""

import hashlib
import json
import re
from uuid import uuid4

from flask import Blueprint, abort, jsonify, request, current_app
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ..models.justcall_webhook import JustCallWebhook
from ..models.justcall_webhook_payload import JustCallWebhookPayload
from ..models.campaign import Campaign
from ..services.helpers import get_session
from ..services.lead_service import create_lead

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/webhooks")


# Explicit whitelists of model fields that may be written via webhook mapping
CAMPAIGN_WRITABLE_FIELDS = {"campaign_name", "status", "client_id"}
LEAD_WRITABLE_FIELDS = {
    "name",
    "phone",
    "address",
    "email",
    "company",
    "secondary_phone",
    "lead_type",
    "caller_name",
    "caller_number",
    "notes",
    "client_id",
    "campaign_id",
    "number_id",
}


def _extract(obj, path):
    current = obj
    for part in path.split("."):
        # Split segments like 'foo[0][1]' into ['foo', '[0]', '[1]']
        tokens = re.split(r"(\[\d+\])", part)
        tokens = [t for t in tokens if t]
        for token in tokens:
            if token.startswith("["):
                index = int(token[1:-1])
                if isinstance(current, list):
                    try:
                        current = current[index]
                    except IndexError:
                        return None
                else:
                    return None
            else:
                if isinstance(current, dict):
                    current = current.get(token)
                else:
                    return None
            if current is None:
                return None
    return current


def _fingerprint_payload(payload) -> str:
    """Return a stable hash for *payload* suitable for deduplication checks."""

    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@webhooks_bp.route("/justcall/<token>", methods=["POST"])
def justcall_webhook(token: str):
    """Receive lead data from JustCall and store it in the database."""
    with get_session() as session:
        webhook = session.query(JustCallWebhook).filter_by(token=token).first()
        if not webhook:
            abort(404)
        payload = request.get_json(silent=True)
        if not isinstance(payload, (list, dict)):
            abort(400, "Invalid JSON payload")
        if isinstance(payload, dict):
            payload = [payload]

        fingerprint = _fingerprint_payload(payload)
        recent_payloads = (
            session.query(JustCallWebhookPayload)
            .filter_by(token_id=webhook.id)
            .order_by(JustCallWebhookPayload.id.desc())
            .limit(20)
            .all()
        )
        if any(_fingerprint_payload(entry.payload) == fingerprint for entry in recent_payloads):
            current_app.logger.info(
                "Ignoring duplicate JustCall payload for token %s", token
            )
            return "", 204

        session.add(JustCallWebhookPayload(token_id=webhook.id, payload=payload))
        mapping = webhook.mapping or {}
        writable_fields = (
            CAMPAIGN_WRITABLE_FIELDS
            if webhook.target_type == "campaign"
            else LEAD_WRITABLE_FIELDS
        )
        for item in payload:
            if mapping:
                # Start with any default data provided, restricting to writable fields
                data: dict = {
                    k: v
                    for k, v in (item.get("data") or {}).items()
                    if k in writable_fields
                }
                for field, path in mapping.items():
                    if webhook.target_type != "campaign" and field == "campaign_id":
                        value = _extract(item, path)
                        if value is not None:
                            campaign = (
                                session.query(Campaign)
                                .filter(
                                    or_(
                                        Campaign.id == value,
                                        Campaign.campaign_name == value,
                                    )
                                )
                                .first()
                            )
                            if campaign:
                                data["campaign_id"] = campaign.id
                                if campaign.client_id and "client_id" not in data:
                                    data["client_id"] = campaign.client_id
                            else:
                                abort(400, f"Campaign not found: {value}")
                        continue
                    # Only allow whitelisted fields to be written
                    if field in writable_fields:
                        data[field] = _extract(item, path)
                        continue
                    # Allow campaign name mapping for lead webhooks
                    if (
                        webhook.target_type != "campaign"
                        and field in {"campaign", "campaign_name"}
                    ):
                        value = _extract(item, path)
                        campaign = (
                            session.query(Campaign)
                            .filter_by(campaign_name=value)
                            .first()
                        )
                        if campaign:
                            data["campaign_id"] = campaign.id
                            # Map the campaign's client to the lead if available
                            if campaign.client_id and "client_id" not in data:
                                data["client_id"] = campaign.client_id
                        continue
                    # Ignore any disallowed fields
                    current_app.logger.debug("Ignoring disallowed field '%s'", field)
                if webhook.target_type == "campaign" and "id" not in data:
                    data["id"] = uuid4().hex
                if webhook.target_type == "campaign":
                    session.add(Campaign(**data))
                else:
                    ok, err = create_lead(
                        name=data.get("name"),
                        phone=data.get("phone"),
                        email=data.get("email"),
                        address=data.get("address"),
                        company=data.get("company"),
                        secondary_phone=data.get("secondary_phone"),
                        campaign_id=data.get("campaign_id"),
                        lead_type=data.get("lead_type"),
                        caller_name=data.get("caller_name"),
                        caller_number=data.get("caller_number"),
                        notes=data.get("notes"),
                        flash_error=False,
                    )
                    if not ok:
                        return jsonify({"error": err}), 409
            else:
                data = item.get("data", {})
                if webhook.target_type == "campaign":
                    session.add(
                        Campaign(
                            id=data.get("id"),
                            campaign_name=data.get("campaign_name"),
                            status=data.get("status"),
                            client_id=data.get("client_id"),
                        )
                    )
                else:
                    cf = data.get("custom_fields") or {}
                    campaign_id = data.get("campaign_id")
                    campaign_name = data.get("campaign_name")
                    if campaign_name:
                        campaign = (
                            session.query(Campaign)
                            .filter_by(campaign_name=campaign_name)
                            .first()
                        )
                        if campaign:
                            campaign_id = campaign.id
                    ok, err = create_lead(
                        name=data.get("client_name"),
                        phone=data.get("client_number") or data.get("phone"),
                        address=data.get("address"),
                        email=data.get("email"),
                        company=cf.get("Company"),
                        secondary_phone=cf.get("Alternate Phone Number"),
                        campaign_id=campaign_id,
                        lead_type=data.get("disposition"),
                        caller_name=data.get("caller_name"),
                        caller_number=data.get("caller_number"),
                        notes=cf.get("Notes") or data.get("notes"),
                        flash_error=False,
                    )
                    if not ok:
                        return jsonify({"error": err}), 409
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            current_app.logger.exception("Integrity error processing JustCall webhook")
            return (
                jsonify(
                    {
                        "error": "Database integrity error",
                        "details": str(exc.orig),
                    }
                ),
                409,
            )
    return "", 204


@webhooks_bp.route("/justcall/<token>/latest", methods=["GET"])
def justcall_latest(token: str):
    """Return the most recent payload received for a webhook token."""
    with get_session() as session:
        webhook = session.query(JustCallWebhook).filter_by(token=token).first()
        if not webhook:
            abort(404)
        payload = (
            session.query(JustCallWebhookPayload)
            .filter_by(token_id=webhook.id)
            .order_by(JustCallWebhookPayload.created_at.desc())
            .first()
        )
        if not payload:
            return jsonify({}), 200
        return jsonify(payload.payload)


@webhooks_bp.route("/justcall/<token>/mapping", methods=["GET"])
def justcall_get_mapping(token: str):
    """Return the saved JSON field mapping for a webhook token."""
    with get_session() as session:
        webhook = session.query(JustCallWebhook).filter_by(token=token).first()
        if not webhook:
            abort(404)
        return jsonify(webhook.mapping or {})


@webhooks_bp.route("/justcall/<token>/mapping", methods=["POST"])
def justcall_save_mapping(token: str):
    """Save a JSON field mapping for a webhook token."""
    mapping = request.get_json(silent=True) or {}
    with get_session() as session:
        webhook = session.query(JustCallWebhook).filter_by(token=token).first()
        if not webhook:
            abort(404)
        webhook.mapping = mapping
        session.add(webhook)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            current_app.logger.exception("Integrity error saving webhook mapping")
            return (
                jsonify(
                    {
                        "error": "Database integrity error",
                        "details": str(exc.orig),
                    }
                ),
                409,
            )
    return "", 204


__all__ = ["webhooks_bp"]
