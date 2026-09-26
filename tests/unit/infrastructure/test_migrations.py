"""Unit tests for Alembic database migration configuration and revisions.

These tests verify that Alembic is properly configured with an async engine,
correct metadata targeting, and that migration revisions exist and can be traversed.
"""

from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_ini_configuration() -> None:
    """Verify that alembic.ini exists and has valid configuration settings.

    Beginner explanation:
    alembic.ini is the main configuration file for Alembic. We check that it exists
    and points to the 'alembic' directory where our migration scripts live.
    """
    ini_path = Path("alembic.ini")
    assert ini_path.exists(), "alembic.ini configuration file must exist in project root"

    config = Config(str(ini_path))
    script_location = config.get_main_option("script_location")
    assert script_location is not None
    assert "alembic" in script_location


def test_alembic_env_targets_base_metadata() -> None:
    """Verify that alembic/env.py configures target_metadata with Base.metadata.

    Beginner explanation:
    Base.metadata contains all tables defined by SQLAlchemy models. By setting
    target_metadata = Base.metadata in env.py, Alembic compares the active database
    schema against our Python models and detects schema changes automatically.
    """
    env_path = Path("alembic/env.py")
    assert env_path.exists(), "alembic/env.py must exist"

    content = env_path.read_text(encoding="utf-8")
    assert "target_metadata = Base.metadata" in content
    assert "from src.core.database import Base, engine" in content
    assert "from src.infrastructure.database.base_model import TimestampMixin" in content
    assert "async with engine.connect() as connection:" in content


def test_initial_empty_migration_exists() -> None:
    """Verify that the initial migration revision was created and is a root revision.

    Beginner explanation:
    Every migration in Alembic has a revision ID and points back to its 'down_revision'
    (the previous revision). The first migration is a 'root' revision, so its
    down_revision must be None.
    """
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    # Get all revisions in the alembic/versions folder
    revisions = list(script.walk_revisions())
    assert len(revisions) >= 1, "At least one migration revision should exist"

    # Find the root revision (down_revision is None)
    initial_rev = revisions[-1]
    assert initial_rev.down_revision is None, "The initial migration must have down_revision=None"
    assert "initial_empty" in initial_rev.doc, (
        f"Initial migration doc should mention 'initial_empty', got: {initial_rev.doc}"
    )
