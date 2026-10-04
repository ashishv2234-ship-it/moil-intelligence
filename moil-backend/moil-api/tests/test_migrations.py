"""Guards against drift: the migrations, run from nothing, must build exactly the tables the models describe."""
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parent.parent


def test_migrations_match_models(tmp_path):
    pytest.importorskip("alembic")
    if not any((ROOT / "alembic" / "versions").glob("*.py")): pytest.skip("No migration yet: run  python -m scripts.make_baseline")
    from alembic import command
    from alembic.autogenerate import compare_metadata
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine
    from app.db.session import Base
    import app.models  # noqa: F401
    url = f"sqlite:///{(tmp_path / 'm.db').as_posix()}"
    cfg = Config(str(ROOT / "alembic.ini")); cfg.set_main_option("script_location", str(ROOT / "alembic")); cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    with engine.connect() as conn: diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == [], f"Models and migrations disagree. Make a new migration: python -m alembic revision --autogenerate -m \"describe the change\". Differences: {diff}"
