"""Authentication related routes."""

from flask import Blueprint, render_template, request, session, redirect

from ..models import SessionLocal
from ..models.user import User
from ..services.auth_service import supabase_config, verify_supabase_token

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET"])
def login_page():  # pragma: no cover - view logic
    """Render the login page or redirect if already logged in."""

    if "uid" in session:
        return redirect("/dashboard")

    config, missing = supabase_config()
    return render_template(
        "login.html", supabase_config=config, missing_keys=missing
    )


@auth_bp.route("/reset-password", methods=["GET"])
def reset_password_page():  # pragma: no cover - view logic
    """Render the reset password page used by Supabase."""

    config, missing = supabase_config()
    return render_template(
        "reset_password.html", supabase_config=config, missing_keys=missing
    )


@auth_bp.route("/sessionLogin", methods=["POST"])
def session_login():  # pragma: no cover - view logic
    """Create a server side session from a Supabase JWT."""

    data = request.get_json(silent=True) or {}
    id_token = data.get("idToken")
    claims = verify_supabase_token(id_token) if id_token else None
    if claims:
        uid = claims.get("sub")
        email = claims.get("email", "") or f"{uid}@example.com"
        db = SessionLocal()
        try:
            # First try to find user by UID
            user = db.query(User).filter_by(uid=uid).first()
            
            # If not found by UID, try to find by email (in case user was pre-created)
            if not user:
                user = db.query(User).filter_by(email=email).first()
                if user:
                    # Update the existing user's UID to match Supabase UID
                    user.uid = uid
                    db.commit()
                    db.refresh(user)
            
            # If still not found, create new user
            if not user:
                user = User(uid=uid, email=email)
                db.add(user)
                db.commit()
                db.refresh(user)
            
            session["uid"] = uid
            session["user_id"] = user.id
            session["is_staff"] = user.is_staff
            session["is_superuser"] = user.is_superuser
            session["permissions"] = [p.path for p in user.permissions]
            return ("", 204)
        except Exception as e:
            db.rollback()
            print(f"Error during login: {e}")
            return ("Internal Server Error", 500)
        finally:
            db.close()
    print("Invalid Supabase token:", id_token)
    return ("Unauthorized", 401)


@auth_bp.route("/logout", methods=["GET"])
def logout():  # pragma: no cover - simple session clear
    """Clear the user session and redirect to the login page."""

    session.clear()
    return redirect("/login")
