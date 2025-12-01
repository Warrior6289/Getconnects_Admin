import re

def test_permission_denied(app_module):
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "user1"
        sess["permissions"] = ["/dashboard"]
    resp = client.get("/clients")
    assert resp.status_code == 403
    assert "don't have permission" in resp.get_data(as_text=True)


def test_navigation_hides_links(app_module):
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "user1"
        sess["permissions"] = ["/dashboard"]
    resp = client.get("/dashboard")
    html = resp.get_data(as_text=True)
    assert re.search(r'href="/clients"', html) is None
    assert re.search(r'href="/dashboard"', html)
