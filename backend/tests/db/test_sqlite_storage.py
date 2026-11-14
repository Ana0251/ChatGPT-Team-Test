"""Independent SQLite files, per-connection FK enforcement and exact IRR amounts."""

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, Text, inspect, text
from sqlalchemy.exc import IntegrityError, StatementError

from app.db.engine import create_sqlite_engine
from app.db.money import ExactRial


def _url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_database_files_are_isolated(tmp_path: Path) -> None:
    first_path = tmp_path / "isolated_a.db"
    second_path = tmp_path / "isolated_b.db"
    first = create_sqlite_engine(_url(first_path))
    second = create_sqlite_engine(_url(second_path))
    try:
        with first.begin() as connection:
            connection.execute(text("CREATE TABLE only_in_a (id INTEGER PRIMARY KEY)"))
            connection.execute(text("INSERT INTO only_in_a (id) VALUES (1)"))
        assert "only_in_a" in inspect(first).get_table_names()
        assert "only_in_a" not in inspect(second).get_table_names()
        assert first_path.is_file()
        assert second_path.is_file()  # inspector opened the second DB
        assert first_path.resolve() != second_path.resolve()
    finally:
        first.dispose()
        second.dispose()


def test_foreign_keys_enforced_on_each_connection(tmp_path: Path) -> None:
    engine = create_sqlite_engine(_url(tmp_path / "foreign_keys.db"))
    try:
        with engine.begin() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            connection.exec_driver_sql("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
            connection.exec_driver_sql(
                "CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL "
                "REFERENCES parent(id))"
            )
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            with pytest.raises(IntegrityError):
                connection.execute(text("INSERT INTO child (id, parent_id) VALUES (1, 999)"))
            connection.rollback()
        engine.dispose()
        with engine.connect() as fresh_connection:
            assert fresh_connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
    finally:
        engine.dispose()


def test_20_digit_rial_and_account_code_are_lossless(tmp_path: Path) -> None:
    engine = create_sqlite_engine(_url(tmp_path / "money.db"))
    metadata = MetaData()
    rows = Table(
        "money_probe",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("rial", ExactRial(), nullable=False),
        Column("account_code", Text, nullable=False),
    )
    exact = "99999999999999999999"
    try:
        metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(
                rows.insert().values(id=1, rial=Decimal(exact), account_code="000001")
            )
            for invalid in (1.5, -1, "0002", "100000000000000000000", "1.00"):
                with pytest.raises((StatementError, ValueError, TypeError)):
                    connection.execute(
                        rows.insert().values(id=2, rial=invalid, account_code="000002")
                    )
        with engine.connect() as connection:
            item = connection.execute(rows.select()).one()
            assert item.rial == Decimal(exact)
            assert item.account_code == "000001"
            assert connection.execute(
                text("SELECT typeof(rial) FROM money_probe WHERE id=1")
            ).scalar_one() == "text"
    finally:
        engine.dispose()


def test_sqlite_only_and_explicit_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESABYAR_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="HESABYAR_DATABASE_URL"):
        create_sqlite_engine()
    with pytest.raises(ValueError, match="only local SQLite"):
        create_sqlite_engine("postgresql://example.invalid/database")
