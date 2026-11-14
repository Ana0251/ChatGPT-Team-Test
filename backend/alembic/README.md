# H-04 — local SQLite / Alembic baseline

Scope: **SQLite local development only**, not an approved production engine. Python 3.14.7 and SQLite 3.50.4 are the owner's reference environment. H-04 never implements H-05 identity, business accounts, tenant membership, or posting.

Run commands **from the repository's `backend` directory**, using an isolated virtual environment:

```powershell
py -3.14 --version
py -3.14 -c "import sqlite3; print(sqlite3.sqlite_version)"
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pip freeze
$env:HESABYAR_DATABASE_URL = 'sqlite:///D:/ChatGPT-Team-Test-H04-data/hesabyar-local.db'
New-Item -ItemType Directory -Force D:\ChatGPT-Team-Test-H04-data | Out-Null
.\.venv\Scripts\python.exe -m alembic -c alembic/alembic.ini current
.\.venv\Scripts\python.exe -m alembic -c alembic/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c alembic/alembic.ini current
.\.venv\Scripts\python.exe -m alembic -c alembic/alembic.ini downgrade base
.\.venv\Scripts\python.exe -m alembic -c alembic/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m pytest -v tests/db
```

For an **independent, disposable migration database** outside the repository, point `HESABYAR_DATABASE_URL` to a unique file first. Never run downgrades against a customer/production DB. The tests themselves use `tmp_path` for isolated SQLite files and override the URL with `monkeypatch`.

Use this read-only schema inspection command before and after each migration (run from backend):

```powershell
.\.venv\Scripts\python.exe -c "from app.db.engine import create_sqlite_engine; from sqlalchemy import inspect; e=create_sqlite_engine(); print('tables=',inspect(e).get_table_names()); print('foreign_keys=',e.connect().exec_driver_sql('PRAGMA foreign_keys').scalar()); e.dispose()"
```

Capture `git rev-parse HEAD`, Python/SQLite/SQLAlchemy/Alembic/Pytest versions, all actual PowerShell stdout/stderr, exit codes, schema snapshots and `pytest` results. Do not call tests PASS without actual execution. No SQLite .db files, secrets or real customer data may be committed. Use a **separate worktree** at the exact PR HEAD to avoid collisions. The baseline intentionally contains only `h04_schema_baseline`; application tables belong to later authorized tasks.

Financial amounts are **canonical nonnegative decimal strings** backed by SQLite TEXT in `app.db.money.ExactRial`, converted to Python `Decimal`; no float, exponent, or amount beyond 20 decimal digits. Account codes remain TEXT (leading zeros preserved). SQLite's NUMERIC affinity is **not** equivalent to PostgreSQL NUMERIC(20,0).

**Deferred:** PostgreSQL row locking, production concurrency/races, native NUMERIC(20,0), multi-company authorization, production-engine recovery/security tests, independent QA. Legacy review sequence: Developer report → Coordinator integration review → QA review; Manager decides on merge.
