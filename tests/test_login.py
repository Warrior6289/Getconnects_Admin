"""Tests for login page behavior."""


def test_login_page_redirects_when_authenticated(app_module):
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "test"
    resp = client.get("/login", follow_redirects=False)
    assert resp.status_code == 302

    assert resp.headers["Location"].endswith("/dashboard")


def test_login_page_accessible_when_anonymous(app_module):
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess.clear()
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Login" in resp.data
    assert b"Forgot password?" in resp.data
