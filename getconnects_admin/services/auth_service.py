"""Authentication related helpers using Supabase."""

import os
import smtplib
from typing import Optional, Dict

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def _get_supabase_client() -> Client:
    """Initialise and return a Supabase client instance."""

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise ValueError("Supabase credentials are not configured")
    return create_client(url, key)


def verify_supabase_token(id_token: str) -> Optional[Dict[str, str]]:
    """Validate *id_token* using Supabase and return its claims.

    Returns ``None`` when verification fails.
    """

    try:
        client = _get_supabase_client()
        user = client.auth.get_user(id_token).user
        return {"sub": user.id, "email": user.email}
    except Exception:  # pragma: no cover - network errors
        return None


def supabase_config() -> tuple[dict, list[str]]:
    """Return Supabase configuration and list missing keys."""

    mapping = {"url": "SUPABASE_URL", "anonKey": "SUPABASE_ANON_KEY"}
    config = {k: os.environ.get(env) for k, env in mapping.items()}
    missing = [k for k, v in config.items() if not v]
    return config, missing


def create_supabase_user(email: str) -> None:
    """Create a user with *email* in Supabase.

    Silently ignores errors as user creation is a best-effort operation
    when managing internal staff accounts.
    """

    try:
        client = _get_supabase_client()
        client.auth.admin.create_user({"email": email})
    except Exception:  # pragma: no cover - network errors
        pass


def send_activation_email(email: str) -> None:
    """Send a password reset link to *email* using Supabase and SMTP."""

    try:
        client = _get_supabase_client()
        link = client.auth.admin.generate_link(type="recovery", email=email).link
    except Exception:  # pragma: no cover - network errors
        return

    server = os.environ.get("SMTP_SERVER")
    if not server:
        print(f"Activation link for {email}: {link}")
        return

    port = int(os.environ.get("SMTP_PORT", "25"))
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    from_addr = os.environ.get("SMTP_FROM", username or "no-reply@example.com")

    try:
        with smtplib.SMTP(server, port) as smtp:
            if username and password:
                smtp.starttls()
                smtp.login(username, password)
            message = (
                "Subject: Activate your account\n\n"
                f"Click the link to set your password: {link}"
            )
            smtp.sendmail(from_addr, email, message)
    except Exception:  # pragma: no cover - SMTP failures
        print(f"Activation link for {email}: {link}")
