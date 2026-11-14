"""Alembic baseline schema verification, including upgrade/downgrade/upgrade."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.db.engine import create_sqlite_engine


def _config() -> Config:
    ini = Path(__file__).resolve().parents[2] / "alembic" / "alembic.ini"
    return Config(str(ini))


def test_upgrade_downgrade_upgrade_uses_isolated_database(
    tmp_path: Path, monkeypatch
) -> None:
    migration_db = tmp_path / "migration_only.db"
    separate_db = tmp_path / "untouched.db"
    monkeypatch.setenv("HESABYAR_DATABASE_URL", f"sqlite:///{migration_db.as_posix()}")
    config = _config()
    migration_engine = create_sqlite_engine()
    untouched_engine = create_sqlite_engine(f"sqlite:///{separate_db.as_posix()}")
    try:
        assert "h04_schema_baseline" not in inspect(migration_engine).get_table_names()
        command.upgrade(config, "head")
        assert "h04_schema_baseline" in inspect(migration_engine).get_table_names()
        with migration_engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "h04_0001"

        command.downgrade(config, "base")
        assert "h04_schema_baseline" not in inspect(migration_engine).get_table_names()

        command.upgrade(config, "head")
        assert "h04_schema_baseline" in inspect(migration_engine).get_table_names()
        assert "h04_schema_baseline" not in inspect(untouched_engine).get_table_names()
        assert migration_db.is_file()
        assert separate_db.is_file()
    finally:
        migration_engine.dispose()
        untouched_engine.dispose()
