"""Alembic async migration environment configuration.

Configures Alembic to run database migrations asynchronously using the shared
SQLAlchemy AsyncEngine and declarative Base metadata from the application core.

For Python beginners:
- This file is the central execution script loaded by Alembic whenever running
  migration commands (`alembic upgrade`, `alembic downgrade`, `alembic revision`).
- It reuses the AsyncEngine from `src.core.database` instead of creating a separate
  connection pool, saving system resources and keeping connection secrets secure.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy.engine import Connection

from alembic import context
# Reuse Base (containing table metadata) and async engine from application core
from src.core.database import Base, engine
# Import base mixins/models to register them with Base.metadata
from src.infrastructure.database.base_model import TimestampMixin  # noqa: F401

# NOTE (Feature 1+): When new ORM models are created (e.g. CategoryModel, ProductModel,
# OrderModel, UserModel), import them here so that Alembic's `--autogenerate`
# can detect their schema definitions via Base.metadata.
# Example:
# from src.infrastructure.database.models import CategoryModel, ProductModel  # noqa: F401

# Alembic Config object, which provides access to values in alembic.ini
config = context.config

# Setup Python logging if config file specifies logging configuration
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support to compare models with the database
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and emits raw SQL DDL statements
    to standard output or a script file without connecting to a live database.
    Useful for code reviews or handing SQL scripts to a Database Administrator (DBA).
    """
    url = str(engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # render_as_batch=True: Required for SQLite schema alterations using temporary tables
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations within an active database connection transaction.

    This function is passed as a synchronous callback to `connection.run_sync(...)`.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Required for SQLite when altering table schemas (adding/modifying/dropping columns)
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using the shared AsyncEngine.

    Reuses the existing AsyncEngine from src.core.database instead of
    creating a new engine from alembic.ini. The async engine integrates
    seamlessly with FastAPI and SQLAlchemy 2.0.
    """
    # Open an async connection from the application's shared engine
    async with engine.connect() as connection:
        # run_sync: safely bridges synchronous Alembic DDL operations inside an async context
        await connection.run_sync(do_run_migrations)

    # Cleanly dispose the connection pool after migration finishes
    await engine.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode by starting the asyncio event loop."""
    asyncio.run(run_async_migrations())


# Alembic checks whether offline flag (--sql) or a direct online connection is used
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


