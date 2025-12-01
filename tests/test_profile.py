from models.user import User


def test_profile_update(app_module, session):
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    user = User(uid="u1", email="u1@example.com", first_name="Old", last_name="Name")
    session.add(user)
    session.commit()
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["uid"] = user.uid
        sess["user_id"] = user.id
    client.post(
        "/settings/profile",
        data={"first_name": "New", "last_name": "Name"},
        follow_redirects=True,
    )
    session.refresh(user)
    assert user.first_name == "New"
