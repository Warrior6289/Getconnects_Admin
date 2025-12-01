"""Tests for Flask CLI commands."""

from models.user import User


def test_create_superuser_command(app_module, session):
    """Initial creation and authorization checks for create-superuser."""

    runner = app_module.app.test_cli_runner()

    # Create the initial superuser; should succeed without actor
    result = runner.invoke(args=["create-superuser", "first@example.com", "--uid", "uid1"])
    assert result.exit_code == 0
    user = session.query(User).filter_by(email="first@example.com").one()
    assert user.is_superuser and user.is_staff

    # Attempt to create another superuser without actor should fail
    result = runner.invoke(args=["create-superuser", "second@example.com", "--uid", "uid2"])
    assert result.exit_code != 0
    assert "actor-email is required" in result.output

    # Provide actor email to authorize promotion
    result = runner.invoke(
        args=[
            "create-superuser",
            "second@example.com",
            "--uid",
            "uid2",
            "--actor-email",
            "first@example.com",
        ]
    )
    assert result.exit_code == 0
    user = session.query(User).filter_by(email="second@example.com").one()
    assert user.is_superuser and user.is_staff

