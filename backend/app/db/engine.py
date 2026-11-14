"""SQLite-only H-04 local database connectivity.

Only absolute, file-backed SQLite URLs with existing parent directories are
accepted. No database is opened at import; PostgreSQL remains deferred.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url


DATABASE_ENV = "HESABYAR_DATABASE_URL"


def create_sqlite_engine(database_url: str | None = None) -> Engine:
    """Create a file-backed SQLite Engine with FK checks on every DBAPI connection."""
    raw_url = database_url if database_url is not None else os.environ.get(DATABASE_ENV)
    if not raw_url:
        raise ValueError(f"{DATABASE_ENV} must be set to an explicit local SQLite URL")

    url = make_url(raw_url)
    if url.get_backend_name() != "sqlite":
        raise ValueError("H-04 supports only local SQLite; final database not selected")

    # Reject in-memory connections, SQLite URI modes (including file::memory:),
    # relative paths, and URL query parameters that could override the location.
    database = url.database
    if not database or database == ":memory:" or url.query or database.startswith("file:"):
        raise ValueError("H-04 requires an absolute file-backed SQLite path (no URI/query)")
    location = Path(database)
    if not location.is_absolute():
        raise ValueError("H-04 SQLite database path must be absolute")
    if not location.parent.is_dir():
        raise ValueError("H-04 SQLite database parent directory must already exist")
    if location.exists() and not location.is_file():
        raise ValueError("H-04 SQLite database path must point to a regular file")

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
