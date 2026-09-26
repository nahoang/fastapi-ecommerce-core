"""Unit tests for Alembic database migration configuration and revisions.

These tests verify that Alembic is properly configured with an async engine,
correct metadata targeting, and that migration revisions exist and can be traversed.

For Python beginners:
- This test file verifies 3 essential configuration requirements:
  1. `alembic.ini` exists and points to the `alembic/` script location.
  2. `alembic/env.py` loads `Base.metadata` and the shared engine correctly.
  3. The migration revision tree has at least one root revision (`initial_empty`).
"""

from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_ini_configuration() -> None:
    """Verify that alembic.ini exists and has valid configuration settings.

    Beginner explanation:
    - `Path("alembic.ini")`: Uses modern object-oriented `pathlib` instead of legacy `os.path`.
    - `assert condition, "Error message"`: If the condition is False, pytest halts and displays the message.
    """
    ini_path = Path("alembic.ini")
    assert ini_path.exists(), "alembic.ini configuration file must exist in project root"

    # Load Alembic Config object from ini file
    config = Config(str(ini_path))
    script_location = config.get_main_option("script_location")
    assert script_location is not None, "script_location option must not be empty"
    assert "alembic" in script_location, "script_location must contain 'alembic'"


def test_alembic_env_targets_base_metadata() -> None:
    """Verify that alembic/env.py configures target_metadata with Base.metadata.

    Beginner explanation:
    - `Base.metadata` contains all tables defined by SQLAlchemy ORM models.
    - Alembic requires `target_metadata = Base.metadata` to detect differences against the database.
    - `read_text(encoding="utf-8")` reads the entire source file as a string to verify key configurations.
    """
    env_path = Path("alembic/env.py")
    assert env_path.exists(), "alembic/env.py must exist"

    content = env_path.read_text(encoding="utf-8")
    assert "target_metadata = Base.metadata" in content, "env.py must assign target_metadata = Base.metadata"
    assert "from src.core.database import Base, engine" in content, "env.py must import Base and engine from core"
    assert "from src.infrastructure.database.base_model import TimestampMixin" in content, "env.py must import base_model"
    assert "async with engine.connect() as connection:" in content, "env.py must open an async engine connection"


def test_initial_empty_migration_exists() -> None:
    """Verify that the initial migration revision was created and is a root revision.

    Beginner explanation:
    - In Alembic, migration files link together via the `down_revision` attribute.
    - The first migration (root) always has `down_revision = None`.
    - `script.walk_revisions()` is a Python Generator that iterates from newest to oldest revisions.
    - Python slice syntax `revisions[-1]` accesses the last item (here, the oldest root revision).
    """
    config = Config("alembic.ini")
    # ScriptDirectory provides the Alembic API to traverse revision files in alembic/versions/
    script = ScriptDirectory.from_config(config)

    # Convert generator to list to inspect length and access by index
    revisions = list(script.walk_revisions())
    assert len(revisions) >= 1, "At least one migration revision should exist in alembic/versions/"

    # Get the last element of the list (Root revision)
    initial_rev = revisions[-1]
    assert initial_rev.down_revision is None, "The initial migration must have down_revision=None"
    assert "initial_empty" in initial_rev.doc, (
        f"Initial migration doc should mention 'initial_empty', got: {initial_rev.doc}"
    )


