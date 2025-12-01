"""Statistics related routes."""

from flask import Blueprint, jsonify

from ..services.stats_service import get_stats, get_leads_by_campaign

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/stats", methods=["GET"])
def stats_index():
    """Return application statistics as JSON."""
    return jsonify(get_stats())


@stats_bp.route("/stats/leads_by_campaign", methods=["GET"])
def stats_leads_by_campaign():
    """Return lead counts grouped by campaign as JSON."""
    return jsonify(get_leads_by_campaign())
