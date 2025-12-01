from models.user import User


def test_staff_management_requires_superuser(app_module):
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "user"
    resp = client.get("/settings/users")
    assert resp.status_code == 403


def test_add_and_update_user(app_module, session, monkeypatch):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = "admin"
        sess["is_superuser"] = True

    called = {"create": None, "send": None}

    def fake_create(email: str) -> None:
        called["create"] = email

    def fake_send(email: str) -> None:
        called["send"] = email

    monkeypatch.setattr(
        "getconnects_admin.routes.settings.create_supabase_user", fake_create
    )
    monkeypatch.setattr(
        "getconnects_admin.routes.settings.send_activation_email", fake_send
    )

    client.post(
        "/settings/users",
        data={
            "action": "add",
            "first_name": "New",
            "last_name": "User",
            "email": "new@example.com",
            "role": "staff",
        },
        follow_redirects=True,
    )
    user = session.query(User).filter_by(email="new@example.com").one()
    assert user.first_name == "New" and user.last_name == "User"
    assert user.uid == "new@example.com"
    assert user.is_staff and not user.is_superuser
    assert called["create"] == "new@example.com"
    assert called["send"] == "new@example.com"

    client.post(
        "/settings/users",
        data={
            "action": "update",
            "user_id": str(user.id),
            "role": "admin",
        },
        follow_redirects=True,
    )
    session.refresh(user)
    assert user.is_staff and user.is_superuser
