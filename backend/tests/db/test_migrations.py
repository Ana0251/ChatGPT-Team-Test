"""Alembic baseline schema proof: tables, columns and constraints through U/D/U."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.db.engine import create_sqlite_engine

BASELINE_TABLE = "h04_schema_baseline"


def _config() -> Config:
    ini = Path(__file__).resolve().parents[2] / "alembic" / "alembic.ini"
    return Config(str(ini))


def _schema_snapshot(engine: Engine) -> dict[str, object] | None:
    """Take a fresh inspector snapshot (do not reuse cached Inspector metadata)."""
    inspector = inspect(engine)
    if BASELINE_TABLE not in inspector.get_table_names():
        return None

    columns = {
        column["name"]: {
            "type": str(column["type"]).upper(),
            "nullable": bool(column["nullable"]),
            "primary_key": int(column["primary_key"]),
        }
        for column in inspector.get_columns(BASELINE_TABLE)
    }
    pk = inspector.get_pk_constraint(BASELINE_TABLE)
    return {
        "columns": columns,
        "primary_key_columns": pk["constrained_columns"],
        "foreign_keys": inspector.get_foreign_keys(BASELINE_TABLE),
        "unique_constraints": inspector.get_unique_constraints(BASELINE_TABLE),
        "check_constraints": inspector.get_check_constraints(BASELINE_TABLE),
    }


def _assert_baseline_contract(snapshot: dict[str, object] | None) -> None:
    assert snapshot is not None
    columns = snapshot["columns"]
    assert set(columns) == {"id", "label"}
    assert columns["id"]["type"] == "INTEGER"
    assert columns["id"]["primary_key"] == 1
    assert columns["label"]["type"] == "TEXT"
    assert columns["label"]["nullable"] is False
    assert columns["label"]["primary_key"] == 0
    assert snapshot["primary_key_columns"] == ["id"]
    assert snapshot["foreign_keys"] == []
    assert snapshot["unique_constraints"] == []
    assert snapshot["check_constraints"] == []


def test_upgrade_downgrade_upgrade_uses_isolated_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    migration_db = tmp_path / "migration_only.db"
    separate_db = tmp_path / "untouched.db"
    monkeypatch.setenv("HESABYAR_DATABASE_URL", f"sqlite:///{migration_db.as_posix()}")
    config = _config()
    migration_engine = create_sqlite_engine()
    untouched_engine = create_sqlite_engine(f"sqlite:///{separate_db.as_posix()}")
    try:
        before = _schema_snapshot(migration_engine)
        assert before is None
        assert _schema_snapshot(untouched_engine) is None

        command.upgrade(config, "h04_0001")
        after_first_upgrade = _schema_snapshot(migration_engine)
        _assert_baseline_contract(after_first_upgrade)
        with migration_engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == "h04_0001"
            # Verify a real declared NOT NULL constraint, not only inspector output.
            with pytest.raises(IntegrityError):
                connection.execute(text("INSERT INTO h04_schema_baseline (id, label) VALUES (1, NULL)"))
            connection.rollback()
        assert _schema_snapshot(untouched_engine) is None

        command.downgrade(config, "base")
        after_downgrade = _schema_snapshot(migration_engine)
        assert after_downgrade is None
        assert _schema_snapshot(untouched_engine) is None

        command.upgrade(config, "h04_0001")
        after_second_upgrade = _schema_snapshot(migration_engine)
        _assert_baseline_contract(after_second_upgrade)
        assert after_second_upgrade == after_first_upgrade
        assert before == after_downgrade
        assert _schema_snapshot(untouched_engine) is None
        assert migration_db.is_file()
        assert separate_db.is_file()
    finally:
        migration_engine.dispose()
        untouched_engine.dispose()
