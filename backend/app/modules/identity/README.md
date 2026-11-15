# H-05 — Internal identity and company-scoped membership (SQLite local)

**Scope:** H-05 only; Framework 1.3.0 review_policy=`coordinator_required`. Frozen OpenAPI `1.0.0-rc.3`, blob SHA `98d34e7bd7b4551c0f429ea5e388781060ceaf63`. All exposed routes are under `/api/v1`. No self-registration, company/fiscal CRUD, global super-admin or default user.

## Local configuration — PRIVATE, never commit

- `HESABYAR_DATABASE_URL`: absolute file-backed SQLite URL, e.g. `sqlite:///D:/ChatGPT-Team-Test-H05-data/test-auth.db`; directory must already exist. Reuse the approved H-04 engine and `PRAGMA foreign_keys=ON`.
- `HESABYAR_ALLOWED_ORIGIN`: exact HTTPS browser origin (e.g. `https://internal.example.com`). Every mutation requires an exact `Origin` header and a session-bound `X-CSRF-Token`. The identity endpoints require HTTPS; plain Uvicorn HTTP is **not** an authenticated deployment. Run behind a correctly configured trusted TLS reverse proxy.
- `HESABYAR_LOGIN_PEPPER`: private stable random 32+ character value, used to HMAC-blind email throttling keys. Must be installed through secret management; no hardcoded production fallback.
- `HESABYAR_OPERATOR_KEY`: private high-entropy 32+ character authorization secret for **out-of-band** first-owner provisioning only. Never expose it to a browser or production UI.
- `HESABYAR_SMTP_HOST`, `HESABYAR_SMTP_PORT` (default 465), `HESABYAR_SMTP_USER`, `HESABYAR_SMTP_PASSWORD`, `HESABYAR_SMTP_FROM`: optional trusted TLS SMTP delivery for private invitation/activation tokens. Invitations are rejected if no private delivery callback or SMTP is configured.
- No credentials, raw CSRF/setup/invitation tokens, plaintext passwords, real email addresses or SQLite `.db` files belong in Git.

The operator's private delivery callback (or configured SMTP) receives a 256-bit random token; **only SHA-256 digests**, company/subject binding, expiry and audit events are persisted. Invitation acceptance requires the authenticated invitee's verified email or the new user's possession of the confidential token delivered to that email. A company owner can invite another owner **of that company only**; admin cannot invite owner.

## Manual Windows PowerShell validation

Use a clean, isolated worktree at **the exact latest PR HEAD**, not a stale SHA. From the root of that worktree:

```powershell
git rev-parse HEAD
cd backend
py -3.14 --version
py -3.14 -c "import sqlite3; print('SQLite:', sqlite3.sqlite_version)"
py -3.14 -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install -e ".[test]"
$LASTEXITCODE
& $python -m pip freeze
& $python -m pytest -v tests/identity tests/test_health.py
$LASTEXITCODE
& $python -m pytest -v tests/db
$LASTEXITCODE
```

The identity tests use Pytest `tmp_path` file-backed SQLite databases, environment monkeypatches and real Alembic upgrades on synthetic companies. They use `https://testserver` with FastAPI TestClient to exercise Secure cookies and Origin validation. Production TLS, SMTP delivery, concurrency and real-company security are **NOT** established by these tests.

**Approved H-04 migration regression exception:** Manager decision `APP-HESABYAR-H05-H04-MIGRATION-TEST-EXCEPTION-20261114-001` and merged PR #28 explicitly added `backend/tests/db/test_migrations.py` to H-05 allowed paths **only to replace two** `command.upgrade(config, "head")` calls with `command.upgrade(config, "h04_0001")`. That correction is already committed in H-05 PR #26 (commit `eea82ad12b07e4e7b8b1c0705acee75c1539c0e3`). All existing schema snapshots, column/type/nullability, PK/FK/unique/check, NOT NULL, downgrade, and DB-isolation assertions remain unchanged. `tests/identity/test_identity_migration.py` separately verifies H-04→H-05→H-04→H-05. Previous owner-run regression at `eea82ad...` passed 24 DB tests; **all changes made after that SHA, including invitation rate limiting, require a fresh rerun** before any updated PASS claim.

For CLI schema evidence (use a unique empty database file **outside the repository**):

```powershell
New-Item -ItemType Directory -Force D:\ChatGPT-Team-Test-H05-data | Out-Null
$env:HESABYAR_DATABASE_URL = "sqlite:///D:/ChatGPT-Team-Test-H05-data/h05-$(Get-Date -Format yyyyMMdd-HHmmss).db"
& $python -m alembic -c alembic/alembic.ini upgrade head
$LASTEXITCODE
& $python -m alembic -c alembic/alembic.ini current
& $python -c "from app.db.engine import create_sqlite_engine; from sqlalchemy import inspect; e=create_sqlite_engine(); print(inspect(e).get_table_names()); c=e.connect(); print('FK=',c.exec_driver_sql('PRAGMA foreign_keys').scalar_one()); c.close(); e.dispose()"
```

Expected (not actual until run): migration `h05_0002` installed after `h04_0001`, FK=1 and identity tables exist. All raw stdout/stderr, exit codes, exact tested SHA and installed versions must be posted to H-05 PR for independent Coordinator and QA review.

## Offline initial owner setup — restricted operator only

A trusted operator first configures the private `HESABYAR_OPERATOR_KEY` and SMTP variables **outside Git** (e.g. Windows user-scoped secret management), and an empty migrated database. From `backend`:

```powershell
$env:HESABYAR_BOOTSTRAP_COMPANY = "Approved Company"
$env:HESABYAR_BOOTSTRAP_EMAIL = "verified-operator@example.com"

@'
import os
from app.db.engine import create_sqlite_engine
from app.modules.identity.delivery import smtp_delivery_from_env
from app.modules.identity.provision import provision_initial_owner

send = smtp_delivery_from_env()
if send is None:
    raise SystemExit("Private TLS SMTP delivery is required")
engine = create_sqlite_engine()
try:
    company, subject = provision_initial_owner(
        engine,
        operator_key=os.environ["HESABYAR_OPERATOR_KEY"],
        company_name=os.environ["HESABYAR_BOOTSTRAP_COMPANY"],
        email=os.environ["HESABYAR_BOOTSTRAP_EMAIL"],
        deliver=send,
    )
    print("First-owner provisioning committed; check private delivery channel")
finally:
    engine.dispose()
'@ | & $python -
```

The command does **not** print raw tokens or credentials. The pending user must manually supply the received token and password to `POST /api/v1/auth/activate` after same-origin CSRF bootstrap, then explicitly log in. Setup tokens expire in 15 minutes, invitations in 48 hours. Only one empty-installation bootstrap is allowed. Operational SMTP failure rolls back the provisioning transaction. During development, tests inject an in-process private delivery callback; this is **not** a production delivery mechanism.

## Security behavior

- Argon2id adaptive password hashes only, no plaintext password persistence; generic login errors and rate limiting (five failed attempts locks email for 15 minutes); HMAC-blinded throttle keys.
- Random 256-bit pre-session/authentication cookie values are stored as hashes. `Secure; HttpOnly; SameSite=Lax`, URL path `/api/v1`; 15-minute anonymous pre-session and 60-minute authenticated session, with server-side expiry and revocation.
- `GET /auth/csrf` returns a token bound to the current cookie-backed session and rotates the CSRF secret. All unsafe identity methods require exact HTTPS Origin and matching header. Session and CSRF are rotated on login/activation; logout invalidates auth session. No auto-replay of unsafe methods.
- Invitation acceptance/redeeming is within SQLite `BEGIN IMMEDIATE` transactions, checking expiry, single use, email, inviter's current company role and company binding before granting membership. No arbitrary tenant IDs can grant access; for inaccessible companies the membership endpoint returns non-disclosing 404.
- **Invitation issuance quota:** every company has at most **50** successful invitations in any rolling **24-hour** window, and each (company, inviter) pair at most **20** in the same window, regardless of distinct recipient addresses. Check counts are based on persisted `h05_audit` `membership_invitation_created` events, including previously accepted/expired invitation tokens; recipients cannot reset the budget by redeeming invites. Counts, insert and audit are serialized inside existing SQLite `BEGIN IMMEDIATE`; failed private delivery rolls back its event and token. Quota rejection uses existing frozen error envelope with HTTP **409** and code **`INVITE_RATE_LIMITED`**, without sending a token or creating a pending invitation. Other companies and other issuers keep independent actor quotas while respecting each company's aggregate limit. Quotas are hard-coded H-05 policy, not environment-adjustable and cannot be bypassed by changing emails. This is **SQLite-local behavior**, not proof of multi-server PostgreSQL concurrency.
- Every mutation is logged as a sanitized audit event; no raw token/password/email is written into audit. SMTP is a trusted delivery boundary and should have its own operational review.

**Pending:** Real Windows owner-run/Pytest evidence **for the new rate-limit SHA**, renewed Coordinator integration review, independent QA and Manager acceptance. **DEFERRED/NOT_TESTED:** PostgreSQL numeric/concurrency/row-locking and any production engine, TLS proxy configuration, end-to-end SMTP, deployment backup/restore and production security review. H-06/H-07/H-08 untouched; never merge without Manager authorization.
