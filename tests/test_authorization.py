def test_clients_requires_staff(app_module):
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "user"
        sess["is_staff"] = False
        sess["permissions"] = []
    resp = client.get("/clients")
    assert resp.status_code == 403


def test_settings_requires_superuser(app_module):
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "user"
    resp = client.get("/settings/justcall")
    assert resp.status_code == 403
