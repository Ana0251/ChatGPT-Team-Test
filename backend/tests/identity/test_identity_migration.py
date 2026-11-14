"""H-05 migration checks, independent of legacy H-04 revision-pinned test."""
from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.engine import create_sqlite_engine


def test_identity_migration_and_reversal(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "identity_migration.db"
    monkeypatch.setenv("HESABYAR_DATABASE_URL", f"sqlite:///{path.as_posix()}")
    ini = Path(__file__).resolve().parents[2] / "alembic" / "alembic.ini"
    config = Config(str(ini))
    engine = create_sqlite_engine()
    identity_tables = {
        "h05_users", "h05_companies", "h05_memberships", "h05_setup_tokens",
        "h05_invitations", "h05_sessions", "h05_login_attempts", "h05_audit",
    }
    try:
        command.upgrade(config, "h04_0001")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "h04_0001"
        before = set(inspect(engine).get_table_names())
        assert "h04_schema_baseline" in before
        assert not identity_tables.intersection(before)

        command.upgrade(config, "head")
        after = set(inspect(engine).get_table_names())
        assert identity_tables <= after
        assert "h04_schema_baseline" in after
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "h05_0002"

        inspector = inspect(engine)
        user_cols = {column["name"]: column for column in inspector.get_columns("h05_users")}
        assert {"id", "email", "password_hash", "active"} <= user_cols.keys()
        assert not user_cols["email"]["nullable"]
        membership_fks = inspector.get_foreign_keys("h05_memberships")
        assert {fk["referred_table"] for fk in membership_fks} == {"h05_users", "h05_companies"}
        session_cols = {column["name"] for column in inspector.get_columns("h05_sessions")}
        assert {"id_hash", "csrf_hash", "expires_at", "revoked_at"} <= session_cols
        assert len(inspector.get_check_constraints("h05_memberships")) >= 1
        with engine.connect() as connection:
            with pytest.raises(IntegrityError):
                connection.execute(text(
                    "INSERT INTO h05_memberships (user_id, company_id, role) "
                    "VALUES ('unknown-user', 'unknown-company', 'owner')"
                ))
            connection.rollback()

        command.downgrade(config, "h04_0001")
        down = set(inspect(engine).get_table_names())
        assert not identity_tables.intersection(down)
        assert "h04_schema_baseline" in down
        command.upgrade(config, "head")
        again = set(inspect(engine).get_table_names())
        assert again == after
    finally:
        engine.dispose()
