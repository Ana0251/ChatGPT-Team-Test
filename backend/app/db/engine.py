"""SQLite-only H-04 local database connectivity.

The database URL must be provided explicitly, and no database is opened at import.
PostgreSQL engine support is deliberately deferred to a later decision.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url


DATABASE_ENV = "HESABYAR_DATABASE_URL"


def create_sqlite_engine(database_url: str | None = None) -> Engine:
    """Construct a SQLite Engine with FK enforcement on *every* DBAPI connection."""
    raw_url = database_url if database_url is not None else os.environ.get(DATABASE_ENV)
    if not raw_url:
        raise ValueError(f"{DATABASE_ENV} must be set to an explicit local SQLite URL")

    url = make_url(raw_url)
    if url.get_backend_name() != "sqlite":
        raise ValueError("H-04 supports only local SQLite; final database not selected")

    engine = create_engine(url, future=True)

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection: object, connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA foreign_keys")
            if cursor.fetchone()[0] != 1:
                raise RuntimeError("SQLite foreign key enforcement could not be enabled")
        finally:
            cursor.close()

    return engine
