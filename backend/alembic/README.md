# H-04 — SQLite local / Alembic baseline (review fixes)

**Scope:** file-backed SQLite only, local development. Reference owner environment: Python 3.14.7, SQLite 3.50.4. No identity, tenant, account or journal tables. PostgreSQL-only tests are **DEFERRED**, not PASS.

## Required Windows PowerShell manual evidence

Use a clean Git worktree of **the exact latest PR #18 HEAD SHA** (record it; do not reuse previous SHA). From the worktree's `backend` directory:

```powershell
git rev-parse HEAD
py -3.14 --version
py -3.14 -c "import sqlite3; print('SQLite:', sqlite3.sqlite_version)"
py -3.14 -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install -e ".[test]"
$LASTEXITCODE
& $python -m pip freeze
& $python -m pytest -v tests/db
$LASTEXITCODE
```

The tests cover file isolation, foreign keys on physical connections, FK violations, invalid SQLite URLs, exact 20-digit IRR storage, invalid money inputs including `Decimal('1E+3')`, and a **schema-level** upgrade → downgrade → upgrade round trip. A created test definition is **not** a PASS until actually run.

### Manual migration snapshots on a disposable DB outside the repository

```powershell
New-Item -ItemType Directory -Force D:\ChatGPT-Team-Test-H04-data | Out-Null
$env:HESABYAR_DATABASE_URL = 'sqlite:///D:/ChatGPT-Team-Test-H04-data/h04-review-only.db'

# Define a repeatable schema inspection command. Run after each stage below.
$schema = @'
from sqlalchemy import inspect
from app.db.engine import create_sqlite_engine
e = create_sqlite_engine()
try:
    with e.connect() as c:
        print("foreign_keys=", c.exec_driver_sql("PRAGMA foreign_keys").scalar_one())
    i = inspect(e)
    tables = i.get_table_names()
    print("tables=", tables)
    if "h04_schema_baseline" in tables:
        t = "h04_schema_baseline"
        print("columns=", [(x["name"], str(x["type"]), x["nullable"], x["primary_key"]) for x in i.get_columns(t)])
        print("primary_key=", i.get_pk_constraint(t))
        print("foreign_keys=", i.get_foreign_keys(t))
        print("unique_constraints=", i.get_unique_constraints(t))
        print("check_constraints=", i.get_check_constraints(t))
finally:
    e.dispose()
'@

$schema | & $python -c "import sys; exec(sys.stdin.read())"
& $python -m alembic -c alembic/alembic.ini upgrade head
$LASTEXITCODE
$schema | & $python -c "import sys; exec(sys.stdin.read())"

& $python -m alembic -c alembic/alembic.ini downgrade base
$LASTEXITCODE
$schema | & $python -c "import sys; exec(sys.stdin.read())"

& $python -m alembic -c alembic/alembic.ini upgrade head
$LASTEXITCODE
$schema | & $python -c "import sys; exec(sys.stdin.read())"
```

Expected (NOT observed until owner execution): no baseline table before migration; afterwards `h04_schema_baseline` with `id INTEGER PRIMARY KEY`, `label TEXT NOT NULL`, no FK/unique/check constraints, and `alembic_version` revision `h04_0001`; after downgrade no baseline table; after second upgrade exactly the same columns/constraints. The `test_migrations.py` test also submits `NULL` as `label` to assert that NOT NULL is actually enforced.

### Explicit input policies

- `HESABYAR_DATABASE_URL` is required. Accept only SQLite URLs pointing to an **absolute file path** whose parent directory already exists. `sqlite:///:memory:`, `sqlite://`, relative paths, SQLite URI/query modes (e.g. `mode=memory&uri=true`), nonexistent parent directories and directories masquerading as files are rejected. No SQLite file is opened on import.
- IRR amounts are canonical, nonnegative whole-rial strings (maximum 20 decimal digits) or integers/`Decimal` with the **same canonical lexical representation**. `Decimal('1000')` is allowed, `Decimal('1E+3')` is **rejected**, not silently normalized to `1000`. Float, fraction, negative, leading-zero amount, and exponent-form string are rejected. SQLite TEXT and Python Decimal preserve high-precision amounts; account codes stay TEXT so leading zeros survive.
- All SQLite physical connections enable and check `PRAGMA foreign_keys=ON`. SQLite's NUMERIC affinity does not prove PostgreSQL NUMERIC(20,0) compatibility.

Capture **actual** stdout/stderr/exit codes and tool versions, latest PR SHA, DB file location (redact sensitive personal paths), independent DB evidence and schema snapshots in PR #18 before claiming PASS. Never downgrade a real or shared database. Do not commit `.db`, credentials, customer data or virtual environments.

**Review routing:** Developer evidence → Coordinator renewed integration review → independent QA → Manager decision. No merge without Manager approval; H-05 remains locked. No final production database engine has been selected.
