"""Alembic async migration environment configuration.

Configures Alembic to run database migrations asynchronously using the shared
SQLAlchemy AsyncEngine and declarative Base metadata from the application core.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy.engine import Connection

from alembic import context
from src.core.database import Base, engine
from src.infrastructure.database.base_model import TimestampMixin  # noqa: F401

# NOTE (Feature 1+): When new ORM models are created (e.g., Category, Product,
# Order, User), import them here so that Alembic's autogenerate can detect their
# schema definitions via Base.metadata.
# Example:
# from src.infrastructure.database.models import CategoryModel, ProductModel  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, emitting
    raw SQL statements to standard output without connecting to a database server.
    """
    url = str(engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations within an active database connection transaction."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using the shared async engine.

    Reuses the existing AsyncEngine from src.core.database instead of
    creating a new engine from alembic.ini configuration.
    """
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await engine.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
