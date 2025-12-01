"""Tests for navigation sidebar highlighting and available links."""

import re


def test_dashboard_nav_item_active(app_module, session):
    """The Dashboard sidebar link should be marked active when visiting /dashboard."""

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"

    resp = test_client.get("/dashboard")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)
    # li element for Dashboard should have the ``active`` class
    assert re.search(r'<li class="nav-item\s*active">\s*<a href="/dashboard"', html)


def test_notification_test_link_visible(app_module, session):
    """The settings menu should include a link to the notification test page."""

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"

    resp = test_client.get("/dashboard")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)
    assert "/settings/notifications/test" in html


def test_notification_templates_link_visible(app_module, session):
    """Settings menu should display a link to manage notification templates."""

    test_client = app_module.app.test_client()
    with test_client.session_transaction() as sess:
        sess["uid"] = "test"

    resp = test_client.get("/dashboard")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)
    assert "/settings/templates" in html
