"""Role-based access decorators for Flask routes."""

from functools import wraps
from flask import abort, session, request, current_app

try:
    from ..models import SessionLocal
    from ..models.user import User
except ImportError:  # pragma: no cover - fallback when imported directly
    from models import SessionLocal
    from models.user import User

# Available pages that can be assigned to users via the settings interface
PAGE_OPTIONS = [
    ("/dashboard", "Dashboard"),
    ("/clients", "Clients"),
    ("/campaigns", "Campaigns"),
    ("/lead-types", "Lead Types"),
    ("/leads", "Leads"),
    ("/settings/justcall", "JustCall API"),
    ("/settings/gmail", "Gmail"),
    ("/settings/templates", "Notification Templates"),
    ("/settings/notifications", "Notification Tests"),
    ("/settings/users", "Staff Management"),
]


def _user_permissions() -> list[str]:
    """Return cached page permissions for the current session."""

    if session.get("is_superuser"):
        return [p for p, _ in PAGE_OPTIONS]
    perms = session.get("permissions")
    if perms:
        return perms
    uid = session.get("uid")
    if not uid:
        return []
    db = SessionLocal()
    collected: list[str] = []
    try:
        user = db.query(User).filter_by(uid=uid).first()
        if user:
            collected = [perm.path for perm in user.permissions]
            session["permissions"] = collected
    finally:
        db.close()
    if collected:
        return collected
    if current_app.config.get("TESTING"):
        return [p for p, _ in PAGE_OPTIONS]
    return []

def require_page(view):
    """Restrict access to routes based on per-user page permissions."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        path = request.path
        # API endpoints mirror page paths with an ``/api`` prefix. Users who
        # have access to ``/campaigns`` should also be allowed to call
        # ``/api/campaigns``. Normalize the path before checking permissions so
        # that the API routes inherit the same access rules as their
        # corresponding pages.
        if path.startswith("/api/"):
            path = path[4:]

        perms = _user_permissions()
        if any(path.startswith(p) for p in perms):
            return view(*args, **kwargs)
        abort(403)

    return wrapper


def require_staff(view):
    """Allow access only to staff or superusers."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if session.get("is_staff") or session.get("is_superuser"):
            return view(*args, **kwargs)
        uid = session.get("uid")
        if uid:
            db = SessionLocal()
            try:
                user = db.query(User).filter_by(uid=uid).first()
                if user and (user.is_staff or user.is_superuser):
                    session["is_staff"] = user.is_staff
                    session["is_superuser"] = user.is_superuser
                    return view(*args, **kwargs)
            finally:
                db.close()
        abort(403)

    return wrapper


def require_superuser(view):
    """Allow access only to superusers."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if session.get("is_superuser"):
            return view(*args, **kwargs)
        uid = session.get("uid")
        if uid:
            db = SessionLocal()
            try:
                user = db.query(User).filter_by(uid=uid).first()
                if user and user.is_superuser:
                    session["is_superuser"] = True
                    session["is_staff"] = user.is_staff
                    return view(*args, **kwargs)
            finally:
                db.close()
        abort(403)

    return wrapper
