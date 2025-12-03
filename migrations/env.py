from logging.config import fileConfig
from configparser import ConfigParser, Interpolation

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import Base from the project's models package after the refactor to
# ensure Alembic has access to the correct metadata and database URL.
from getconnects_admin.models import Base, DATABASE_URL

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Disable interpolation to prevent ConfigParser from interpreting % characters
# in DATABASE_URL (which may contain URL-encoded characters like %24, %3D, etc.)
# This is necessary because Supabase connection strings contain URL-encoded characters
# We use a no-op interpolation class that doesn't perform any interpolation
class NoInterpolation(Interpolation):
    """A no-op interpolation class that doesn't perform any interpolation."""
    def before_get(self, parser, section, option, value, defaults):
        return value
    def before_set(self, parser, section, option, value):
        return value
    def before_read(self, parser, section, option, value):
        return value

if hasattr(config, 'file_config') and isinstance(config.file_config, ConfigParser):
    # Replace interpolation with a no-op class
    config.file_config._interpolation = NoInterpolation()

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", DATABASE_URL)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
