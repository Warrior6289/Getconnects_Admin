"""Database session and base model configuration."""

import os
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables so DATABASE_URL is available for the application
load_dotenv()

# Attempt optional PostgreSQL driver import; allow absence for SQLite usage
try:  # pragma: no cover - optional dependency
    import psycopg2  # noqa: F401
except Exception:  # pragma: no cover - ignore missing driver
    pass

# Determine database URL, defaulting to in-memory SQLite when unset
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")
# Render and other providers often supply connection strings beginning with
# ``postgres://`` which SQLAlchemy doesn't recognise. Normalise this to
# ``postgresql://`` so users can paste the URL directly from the hosting
# dashboard without additional tweaks.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if not DATABASE_URL.startswith(("postgresql", "sqlite")):
    raise RuntimeError("DATABASE_URL must be a valid PostgreSQL or SQLite URL")

# When using Supabase's pooler (port 6543), the connection string must include
# the project identifier via ``options=project=<project_ref>``. Validate and
# raise a descriptive error if it's missing to prevent confusing connection
# failures later on.
if DATABASE_URL.startswith("postgresql"):
    parsed = urlparse(DATABASE_URL)
    hostname = parsed.hostname or ""
    if parsed.port == 6543 and "supabase" in hostname:
        options = parse_qs(parsed.query).get("options", [])
        if not any(opt.startswith("project=") for opt in options):
            raise RuntimeError(
                "Supabase pooler connections require 'options=project=<project_ref>' in DATABASE_URL"
            )

# Engine and session factory shared across the application
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Declarative base for all ORM models
Base = declarative_base()

__all__ = ["Base", "SessionLocal", "engine", "DATABASE_URL"]
