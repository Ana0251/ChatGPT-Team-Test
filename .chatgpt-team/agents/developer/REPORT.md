# developer / REPORT

## 2026-11-14 — H-02 read-only API contract consumer review

**Decision:** CHANGES_REQUIRED — NOT ACKNOWLEDGED FOR FREEZE.
**Authorized by:** APP-HESABYAR-W0-CONTRACT-REVIEW-20261114-001.
**PR:** https://github.com/Ana0251/ChatGPT-Team-Test/pull/1
**Reviewed version:** `1.0.0-rc.2`
**Reviewed OpenAPI blob SHA:** `c7d45ebfb715aea6960f130648ebfde148c93e54`
**PR head before reporting:** `d0067c98c6c5fc2f883dbf0baf715ad797818119`

### Findings
1. **BLOCKER — detail trial balance completeness.** `docs/architecture/README.md` explicitly allows posting to a postable SUBSIDIARY without DETAIL children; `docs/contracts/openapi.yaml` `TrialBalance` specifies exactly-one ancestor at requested `level=detail`. Such a subsidiary has no detail ancestor. A direct-posted movement may disappear from detail rows and produce misleading `totals`/Dr=Cr claims. Define `detail` to include all postable leaves with actual `account_level` per row (or clearly scope an intentionally partial report, without implying global balance); demonstrate a mixed posting worked fixture and totals over all filters independent of pagination. For example: subsidiary-only A debit 100, detail B credit 100: at `detail` both must remain visible and totals debit=credit=100 if it is promised as a complete trial balance.
2. **BLOCKER — company owner invitation contradiction.** `POST /companies/{companyId}/members` allows existing company owner to invite a new email as `owner`, while `POST /auth/invitations/activate` says "Never creates owner". Clarify that authorized invitations may grant company-scoped owner membership to an activated new user, never global/super-admin privileges, OR expressly prohibit owner invitations to new addresses in both endpoints. Revalidate inviter permissions and immutable token binding atomically.
3. **BLOCKER — complete OpenAPI validation absent.** Validation evidence reports `js-yaml 4.1.0` PASS and substituted-OAI/Ajv2020 structural/schema syntax PASS (69 schema checks, 23 paths, 33 operations, 236 references). The untouched official OpenAPI 3.1 dialect evaluation is `NOT_PASSED` (329 errors), and documented Node CLI reproduction was not executed. Run an independent OpenAPI 3.1-compliant validator against unchanged blob; record validator version, executed command, output and exact SHA. Do not call a modified-dialect PASS unqualified specification conformance.
4. **Security implementation requirements (nonblocking contract review notes):** Session must use HttpOnly/Secure/SameSite, server-side company-membership authorization for every object (including invited company/role), origin-and-cookie-bound CSRF for unsafe methods including anonymous activation, rotation at authentication, token hash/expiry/single-use and transactional consumption; reject cross-company IDs with non-disclosing 404. All of this is design only; not penetration tested.
5. **Accounting implementation requirements (nonblocking notes):** IRR decimal strings parsed to Decimal, persisted as NUMERIC(20,0), no floats; POSTED-only ledgers, excluded drafts, linked reversals, transaction-safe exactly-once posting/numbering, period-close lock protocol and pre-pagination report totals. F1/F2/F3 plus mixed subsidiary/detail leaf fixture are essential eventual PostgreSQL/HTTP tests.

### Disposition and authorization boundaries
Readable and largely implementable contract shape, but **no explicit consumer acceptance** of this SHA due to the above blockers. Re-review after Coordinator revises and provides new final SHA. This is documentation review, **not** source implementation, independent QA, CI PASS, or Manager freeze. H-03 and W1 remain unauthorized. No application, contracts, TASKS/WAVES or other agents' files changed.


## 2026-11-14 — H-02 rc.3 read-only Developer consumer re-review

**Decision: APPROVED / ACKNOWLEDGED FOR CONTRACT CONSUMPTION ONLY** (not PR merge approval, runtime PASS, QA PASS, Manager freeze or W0 exit).
- Manager authorization: `APP-HESABYAR-W0-RC3-REVIEW-20261114-001`.
- PR: https://github.com/Ana0251/ChatGPT-Team-Test/pull/1
- Version: **`1.0.0-rc.3`**.
- Exact OpenAPI blob SHA checked directly against GitHub: **`98d34e7bd7b4551c0f429ea5e388781060ceaf63`**.
- PR head at verification: `586f7b70e6280264e9c423b540a2a2a4306b8cc4`.

### Resolved prior Developer blockers
1. **Detail-level trial balance:** `level=detail` is explicitly the complete posting-leaf set (DETAIL leaves and direct-postable SUBSIDIARY without DETAIL child), with actual `account_level` and `account_name`. Source rows are counted exactly once, and `TrialBalanceTotals` is calculated over authorized filtered population before pagination. `docs/contracts/TRIAL_BALANCE_FIXTURE.md` documents subsidiary A debit 100 and detail B credit 100, with two pages and shared totals 100/100. This resolves the rc.2 missing-leaf contract contradiction; the fixture is not an executed test.
2. **Company-owner invitation:** `/companies/{companyId}/members`, `/auth/invitations/activate` and `/auth/invitations/accept` now consistently allow a new principal to gain only the bound company's owner membership when a currently authorized existing owner issued the invite. Inviter authority is rechecked atomically; admins cannot issue owner invitations; no global or super-admin grant.
3. **CSRF / errors:** Anonymous pre-session and authenticated session CSRF binding, same-origin enforcement, rotation at login, safe one-time token refresh and human resubmission without blind mutation replay are specified. Stable `ErrorCode` and `FieldIssue` include JSON Pointer fields and zero-based `line_index`. `JournalWarning` is structured; journal totals are always present. `Movement` provides stable `line_id`, line_index, description and account metadata. Inclusive Jalali UI dates vs exclusive Gregorian API bounds are documented.
4. **Independent OpenAPI evidence:** `VALIDATION.md` and `validation-result.json` report actual execution of `@apidevtools/swagger-parser 11.0.0` vendor **schema-validation function** against *unchanged* rc.3 YAML, with PASS, source/version/SHA and qualified limitations. Supplemental js-yaml/Ajv checker reports 23 paths, 33 operations, 18 CSRF-protected mutations, 239 refs, 72 syntax checks, zero findings. Full async vendor dereference, Node CLI, unchanged OAI dialect resolution, CI, runtime HTTP/DB tests and independent QA are **NOT_RUN/NOT_PASSED as applicable**; this is adequate for the authorized contract-consumer review, not full specification/runtime certification.

### Reviewer disposition
**No remaining blocking consumer-contract finding** within the approved re-review scope. Explicit Developer acknowledgment of **only** `1.0.0-rc.3` / SHA `98d34e7bd7b4551c0f429ea5e388781060ceaf63`. Any subsequent OpenAPI blob change invalidates this acknowledgment and requires new review. A reproducible CI/OpenAPI gate, independent PR review, UI/UX acknowledgment, Manager freeze/W0 exit and main branch protection remain external gates. **H-03 and W1 remain unauthorized.** No product code, contract, other-agent reports or TASKS/WAVES modified.


## 2026-11-14 — H-03 W1 FastAPI backend foundation submitted for manual validation

**Authorization verified on main:** `APP-HESABYAR-W1-ENTRY-20261114-001`; W0=COMPLETED, W1=AUTHORIZED_NOT_STARTED / entry_authorized=true; H-03=AUTHORIZED_NOT_STARTED / start_authorized=true; H-01 GATE_EVIDENCED and H-02 COMPLETED. The PM Assistant entry PR was merged into base main at `6f3ebe279a43cfe50ba6a5daf341728c85511464`.

- Task: H-03, owner Developer, W1 (H-04/H-05 and other tasks excluded).
- Branch: `feature/h-03-fastapi-health-foundation`, base `main`.
- Pull Request: https://github.com/Ana0251/ChatGPT-Team-Test/pull/7 (OPEN, UNMERGED, manager review required).
- Proposed implementation commit (before adding this report): `70dd275ddd3f7265db9c725282cc94cb59db6af6`.
- Contract unchanged: H-02 frozen OpenAPI `1.0.0-rc.3`, blob `98d34e7bd7b4551c0f429ea5e388781060ceaf63`.

### Exact files and read-back blob SHA
- `backend/pyproject.toml`: `b9fff20e9f05dfdff6ce0b88898e17000601b995`. Python >=3.11, FastAPI and Uvicorn, Pytest/HTTPX test extra and packaging.
- `backend/app/core/config.py`: `3fac71559a09d107f2bfd9ec1b956a45b805f302`. Frozen Settings dataclass and environment variables HESABYAR_APP_NAME/HESABYAR_APP_ENV (defaults Hesabyar API/development); no secrets.
- `backend/app/main.py`: `003db753962ea908f088af955b0c4ff698c2503d`. Minimal `create_app`, `app`, `GET /health` returning JSON `{"status":"ok"}`; no DB/auth.
- `backend/tests/test_health.py`: `9d1cb910a7b349f1f186204052ba71a04839122c`. Three tests for health JSON/status/content-type, configurable OpenAPI title and unknown route 404.

**Observed verification:** GitHub fetch read-back of these four blob SHAs, and compare base to implementation HEAD showing precisely four added permitted files with 97 added lines, no excluded H-04/DB/auth/contract/workflow files. This is repository-integrity evidence only.

**Manual tests:** `NOT_RUN` in this GitHub-only session. No dependency installation, Pytest process, Uvicorn process, live HTTP call, CI/Actions, independent QA, or security/accounting testing was performed. Expected outputs are NOT actual PASS evidence. Detailed commands are in PR #7 description. On a clean Windows PowerShell worktree at exact final PR HEAD: inspect Python `py -3.11 --version`; create venv; `python -m pip install -e ".[test]"`; `python -m pip freeze`; `python -m pytest -v tests/test_health.py`; `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`; second PowerShell `Invoke-RestMethod http://127.0.0.1:8000/health` and `Invoke-WebRequest` for HTTP status. Capture stdout/stderr, process exit codes, tool versions, tested git SHA and PR comment. If failures occur, report FAIL and fix on same H-03 branch only.

**Disposition:** IMPLEMENTATION SUBMITTED / PENDING_MANUAL_VALIDATION_AND_MANAGER_REVIEW. H-03 not claimed COMPLETED; no ledger changed, no W1 exit, no merge. H-04, DB/migrations, H-05/auth and unrelated work remain unauthorized. GitHub Actions optional, not performed.


## 2026-11-14 — H-04 SQLite / SQLAlchemy 2 / Alembic baseline (Framework 1.3.0)

**Owner:** Developer; **review policy:** legacy Coordinator → QA.  
**Authorized:** `APP-HESABYAR-W1-H04-H18-ENTRY-20261114-001` + `APP-HESABYAR-DB-LOCAL-SQLITE-20261114-001`. Formal main ledger: H-03 COMPLETED; H-04 AUTHORIZED_NOT_STARTED and start_authorized=true; W1 entry_authorized=true. `FRAMEWORK_VERSION.json=1.3.0`.  
**PR:** https://github.com/Ana0251/ChatGPT-Team-Test/pull/18  
**Branch:** `feature/h-04-sqlite-alembic-baseline`  
**Base main SHA before work:** `a972e31e0f108b97097e26822ceecb14b6e0d1a9`  
**Source commit before this report:** `bece767b72ec86bf1492dfd8e0c9a43a2c2a74d8`.

### Implementation scope and verified paths
Exactly nine H-04-authorized paths, checked with GitHub compare (9 commits ahead, 0 behind at implementation head):
- `backend/pyproject.toml`: SQLAlchemy >=2.0.44,<3 and Alembic >=1.17,<2 appended while preserving H-03 dependencies.
- `backend/app/db/engine.py`: explicit `HESABYAR_DATABASE_URL` SQLite engine and SQLAlchemy connect listener enabling + verifying `PRAGMA foreign_keys=ON` on every new physical connection; rejects absent/other engine URLs.
- `backend/app/db/money.py`: `ExactRial` Text-backed canonical 0..(10^20-1) IRR representation and Decimal conversion; forbids float/non-integer/exponent/negative and avoids SQLite NUMERIC affinity loss.
- `backend/alembic/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/h-04_0001_baseline.py`: SQLite-only Alembic environment, reversible initial infrastructure marker table `h04_schema_baseline`; no domain tables.
- `backend/tests/db/test_sqlite_storage.py`: file DB isolation, distinct physical FK connection checks, FK integrity rejection, lossless 20-digit monetary string/leading-zero code test, absent/unsupported URL checks.
- `backend/tests/db/test_migrations.py`: isolated database migration `upgrade → downgrade → upgrade`, table before/after verification, revision ID verification, untouched second database.
- `backend/alembic/README.md`: documented owner-reproducible PowerShell commands, schema inspection, SQLAlchemy versions, downgrade and limitations.

### Execution and evidence accuracy
**Source/diff checks: VERIFIED** using GitHub compare and blob read-back. No out-of-scope files, no committed .db/credentials. Attempted external checkout via `git clone --depth 1 --branch feature/h-04-sqlite-alembic-baseline` but isolated tool container could not resolve github.com (`fatal: Could not resolve host: github.com`; command exit 128), therefore **NO downloaded runtime tests were performed here**. The local container Python 3.13.5 / SQLite differs from the user's Python 3.14.7 / SQLite 3.50.4 and does not constitute acceptance evidence.

**Actual SQLAlchemy/Pytest/Alembic execution on user's Windows: NOT_RUN.** Do not infer PASS. Required next evidence: exact final PR HEAD SHA, Python/SQLite/SQLAlchemy/Alembic/Pytest versions, real `pytest -v tests/db` output/exit code, migration `upgrade/downgrade/upgrade` outputs plus before/after schema table differences, per-connection FK PRAGMA and isolation checks. PowerShell steps in PR #18 and `backend/alembic/README.md`.

**No H-05, real tenancy, business-account migrations, auth, multi-company security, or production setup** were implemented. PostgreSQL row-locking, `NUMERIC(20,0)`, production transaction race tests and engine selection are **DEFERRED/NOT_TESTED**, not PASS; SQLite is a manager-approved temporary local exception only.

**H-04 disposition:** CODE SUBMITTED / PENDING MANUAL VALIDATION; owner report to **Coordinator first**, then **independent QA** and Manager approval. H-04 status ledger untouched; no merge or W1 completion claimed.


## 2026-11-14 — H-04 revision in response to Coordinator review PR #18

**Review source:** Coordinator PR #18 comment `6879348645` (2026-11-14); disposition CHANGES_REQUIRED / OWNER_REPORTED_EXECUTION_OUTPUT_UNVERIFIED.  
**Authorization:** Main `.chatgpt-team/FRAMEWORK_VERSION.json` version `1.3.0`; main H-04 `AUTHORIZED_NOT_STARTED`/`start_authorized=true`; W1 `entry_authorized=true`; H-03 `COMPLETED`; local SQLite exception `APP-HESABYAR-DB-LOCAL-SQLITE-20261114-001`.  
**PR:** https://github.com/Ana0251/ChatGPT-Team-Test/pull/18, existing `feature/h-04-sqlite-alembic-baseline` (never main).  
**Original reviewed head:** `338d004aa13ad1541560d7b7a5efe2fb114c904d`.

### Corrections mapped to Coordinator findings

1. **Local file-only SQLite URL:** `backend/app/db/engine.py` checks `make_url` backend SQLite, requires an absolute file path, existing parent folder, existing file if present must be a regular file; rejects `:memory:`, missing location, relative path, SQLite URI mode/query (including URI memory), missing parent, and a directory as the target. Existing per-DBAPI-connection foreign_keys PRAGMA remains. `backend/tests/db/test_sqlite_storage.py` adds positive file-path test and parameterized negative tests.
2. **Canonical Decimal exponent policy:** `ExactRial.process_bind_param` now validates `str(Decimal)` without normalization (previous `format(value, 'f')` normalized exponent away). `Decimal('1E+3')`, `Decimal('0E+3')`, scientific-notation strings and fractional decimal forms are explicitly rejected; `Decimal('1000')`, canonical integers/strings remain allowed; floats are prohibited. Additional negative persistence tests assert failed inserts do not leave a row, and 20-digit amounts remain SQLite TEXT and Decimal.
3. **Real schema comparison on Alembic round trip:** `backend/tests/db/test_migrations.py` takes fresh SQLAlchemy Inspector snapshots of table columns (names/types/nullable/PK flags), PK constrained columns, foreign/unique/check constraints before, after first upgrade, after downgrade, after second upgrade. It asserts complete expected baseline schema, equal first/second snapshots, disappearance on downgrade, a real rejected NULL label insertion, and untouched independent DB. `backend/alembic/README.md` now contains PowerShell schema snapshots at each migration stage with explicit constraints.

**Code change commits (before report):** `708484984318f7327d22d28177c9b40a7016e133` (engine), `3a10d038537fb4fe89258d1a321e95fc6d244307` (money), `33c52075e2c9b1842d7dc016dd5820488c508ee3` (storage tests), `7e9667e6e7abe43b483cba1b45bcf220e25df011` (migration tests), `32b700adada00afefad702371dd3c6b99139ec19` (manual evidence guide).

### Test/approval truth
**This revision contains new test definitions, NOT observed test passes.** No Windows Python 3.14.7 / SQLite 3.50.4 Pytest/Alembic stdout/stderr, real exit codes, or owner command transcript has been delivered to this Developer conversation or PR at the time of review. Status: **NOT_TESTED / PENDING_OWNER_EVIDENCE**. Earlier owner statement of execution is **OWNER_REPORTED / NOT VERIFIED**; no PASS claim.

Request Coordinator **re-review of new PR HEAD** and verification of real owner manual evidence before QA. Legacy framework 1.3.0 order: Developer → Coordinator integration review → independent QA; Manager final gate. `TASKS.json` and `WAVES.json` untouched. H-04 NOT_COMPLETED, PR remains open/unmerged; H-05 and other tasks not started. PostgreSQL NUMERIC(20,0)/locking/production engine tests DEFERRED, not PASS.


## 2026-11-14 — H-05 Identity, session, CSRF and company membership (Framework 1.3.0)

**Authorization / decision:** `APP-HESABYAR-W1-H05-ENTRY-20261114-001`. PR #24 Manager decision merged at `cd7ee63b1e7615d50b046c1470417fe5562712ff`; PR #25 PM Assistant ledger sync merged at `a1a9f537533c56448a7753377e4334f84c0ceb42`. `main` records `H-04=COMPLETED`, `H-05=AUTHORIZED_NOT_STARTED`, `start_authorized=true`, `validation_status=NOT_TESTED` and `review_policy=coordinator_required`. `W1.entry_authorized=true`; H-06/H-07/H-08 stay locked. Framework version `1.3.0`.  
**Frozen contract:** `docs/contracts/openapi.yaml` version `1.0.0-rc.3`, unchanged Git blob `98d34e7bd7b4551c0f429ea5e388781060ceaf63`. Approved H-18 design `design/specs/identity/AUTH_AND_INVITATIONS.md`, `SESSION_STATES.md` read from `main`.  
**Branch:** `feature/h-05-identity-security`, base `main@a1a9f537533c56448a7753377e4334f84c0ceb42`.  
**PR:** https://github.com/Ana0251/ChatGPT-Team-Test/pull/26 — OPEN/UNMERGED (Manager merge gate).  
**Latest implementation HEAD before this report:** `9351aa9bce305a40a862db9fcf66cb004069340a`.

### Authorized-file implementation
- `backend/app/modules/identity/router.py`: contract routes under `/api/v1`: GET CSRF, POST login, initial owner activate, new-invitee activate, existing-invitee accept, logout, GET me and GET/POST company memberships; structured error codes and 422 field issues. No H-06/company CRUD.
- `backend/app/modules/identity/security.py`: Argon2id adaptive password hashing and strength rules; normalized emails; random 256-bit secrets, hash-only storage; per-session **HMAC-bound** CSRF (nonce, session, trusted HTTPS origin and session expiry) plus stored hash; HMAC-based blinded email throttle keys, no raw credential logging.
- `backend/app/modules/identity/store.py` and `tables.py`: SQLite SQLAlchemy 2 identity tables, short atomic `BEGIN IMMEDIATE` membership/token transactions, hashed cookie-session IDs, sessions/CSRF expiry and revocation, company membership checks, safe audit events.
- `backend/app/modules/identity/provision.py`: operator-key-gated, audited out-of-band initial company/owner provisioning only on empty installation, 15-minute company/owner-bound single-use setup token, private delivery callback; no default credentials/public setup endpoint.
- `backend/app/modules/identity/delivery.py`: optional private SMTP_SSL token delivery, no token in API response, database, logs or URLs; absent delivery fails closed.
- `backend/alembic/versions/h-05_0002_identity.py`: new unique identity migration extending H-04 revision, no changes to previous migration or `backend/alembic/env.py`.
- `backend/tests/identity/test_auth_flows.py`: disposable SQLite tests for bootstrap token/reuse/expiry, login good/bad and rate limiting, Argon2id, 401/403/409/422, CSRF/Origin/cookie/rotations, logout/revocation and expired sessions, new/existing invitations, company owner-only invites, viewer/admin restrictions, wrong-target email, revoked inviter, cross-tenant 404, absent SMTP fail-closed, and HMAC binding.
- `backend/tests/identity/test_identity_migration.py`: H04→H05→H04→H05 Alembic migration/schema/FK checks.
- `backend/app/modules/identity/README.md`: Windows PowerShell versions/commands, first-owner operator + SMTP setup, environment and documented known regression limitation.
- `backend/app/main.py`: **only two lines** import/register Identity Router, preserves H-03 `/health`.
- `backend/pyproject.toml`: **only Argon2 dependency** added; no other shared changes.

**Verified repository scope:** GitHub compare against authorized main base shows only the above H-05 allowed paths (12 code/test/docs paths) before this report; frozen OpenAPI blob unchanged. H-05 added no changes to `backend/app/core/config.py`, `backend/app/db/**`, any existing H-04 migration, frontend/design/OpenAPI, PM ledgers or other agents' reports. No DB files, private customer data or real credentials committed.

### Test evidence — strict honesty
**GitHub source/read-back/scope verification: OBSERVED.**  
**Python 3.14.7 / SQLite 3.50.4 owner Windows real execution of the new H-05 code: NOT_RUN / NOT_VERIFIED.** No `pytest` stdout/stderr or exit codes were returned in this conversation and no QA-run has occurred. New test definitions are not evidence of PASS. No live TLS SMTP, cross-tenant external attack simulation or penetration QA claimed.

Manual reproducible steps for exact **final** PR HEAD in `backend/app/modules/identity/README.md`: `py -3.14 --version`, `py -3.14 -c "import sqlite3; print(sqlite3.sqlite_version)"`, fresh venv `pip install -e ".[test]"`, `pip freeze`, `python -m pytest -v tests/identity tests/test_health.py`, `python -m pytest -v tests/db`; migration `upgrade head`, `current`, schema/FK snapshot. Capture exact SHA, tool versions, raw outputs/exit codes, runner identity and redacted evidence in PR. Actual results pending.

**Known H-04 regression conflict — explicit blocker until Manager scope decision:** Existing `backend/tests/db/test_migrations.py` expects `alembic upgrade head` to yield `h04_0001`; with correct H-05 revision `h05_0002` appended, `head` yields `h05_0002`. The old assertion is revision-pinned and likely fails under the new head. H-04 test file is outside H-05 allowed paths and remains untouched. Need Manager-authorized H-04 regression-test correction (test H-04 revision explicitly) before full H-03/H-04/H-05 regression acceptance. Do not claim legacy H-04 tests PASS on new branch.

**Deferred / limitations:** SQLite development-only `BEGIN IMMEDIATE` does not prove PostgreSQL row locking/concurrency; production database, backup/restore, external SMTP reliability, HTTPS trusted reverse-proxy integration, penetration testing and full security/tenant QA **DEFERRED/NOT_TESTED**. Identity-only synthetic company anchor tables will require Coordinator integration review with H-06 company module before any future company CRUD; H-06 itself remains unauthorized.

**H-05 disposition:** IMPLEMENTATION SUBMITTED FOR COORDINATOR REVIEW / NOT COMPLETED; independent QA follows Coordinator per `coordinator_required`, and only Manager may authorize PR merge. H-06–H-08 and other locked tasks untouched. No automatic QA PASS or W1 completion.


## 2026-11-14 — H-05 Windows failure triage; missing invitation token import fixed

**Input: OWNER-REPORTED manual execution (not QA and not personally reproduced by Developer)**, original exact source HEAD `50f2e937b047aa3abba1fa6eb36faa86671d70c9`. Dependency installation reported success / Exit Code 0; identity+health Pytest: **15 passed, 8 failed, Exit Code 1**; legacy H-04 Pytest: **23 passed, 1 failed, Exit Code 1**. No full test traces have been supplied here; failure causes beyond the two identified issues cannot be certified. H-05 formal acceptance remains `NOT_TESTED`.

**Fix 1 (H-05 allowed file only):** In `backend/app/modules/identity/router.py`, add `new_secret` to the existing imports from `app.modules.identity.security`. The invitation creation path calls `raw = new_secret()` (line 365 at original HEAD); previous code lacked this name binding. Commit `bd452c6cac0667d9cf1d10500b2e55718f7c3c3c`. Source read-back confirms the import is now present and `security.py` defines the function. No change to token length/entropy, hash-only persistence, company role checks, invitation expiry, or private delivery. Other invitation-related tests are already present, but **NOT RE-RUN** after this fix. The 8 earlier failures remain FAIL evidence, not converted into PASS. Full new-SHA rerun and raw failure traces are required to identify any additional problem.

**Finding 2 (not fixed; outside H-05 scope):** `backend/tests/db/test_migrations.py` has two `command.upgrade(config, "head")` calls while its expected revision remains `h04_0001`. With the authorized subsequent `h05_0002` revision, `head` now denotes H-05. **Narrow Manager authorization proposal:** change exactly those **two invocations** to `command.upgrade(config, "h04_0001")` in the H-04-owned test; leave the assertion of revision `h04_0001`, fresh Inspector snapshots, column names/types/nullability, PK/FK/unique/check constraints, NOT NULL enforcement, downgrade-to-base, equal post-upgrade snapshots and untouched independent DB unchanged. H-05's own migration test independently covers H04→H05→H04→H05. No H-04 edit executed by Developer pending explicit Manager approval.

**Disposition / review:** Source import correction committed, user-reported tests FAILED, rerun on new final PR HEAD pending, review by Coordinator then independent QA. H-05 not completed or merged; no changes to H-04, prior migrations, OpenAPI, other tasks or ledgers. Legacy H-04 failure is a separate revision-pinned regression gate, not permission to weaken assertions.


## 2026-11-15 — H-05 Coordinator P1 invitation issuance rate-limit remediation

**Coordinator:** PR #29 merged `0c4e357971f3c7caf2ca37a65ca96b883fe23e63`; report status **FAIL / CHANGES_REQUIRED** against H-05 `eea82ad12b07e4e7b8b1c0705acee75c1539c0e3`. Frozen rc.3 contract requires "Limit invitations"; prior same-address duplicate rejection did not limit distinct recipients. Manager expressly authorized only this remediation, tests and stale H-04 README correction on existing H-05 PR #26, without changing contracts or historical migrations.

**Implemented under authorized H-05 files only:**
- `backend/app/modules/identity/router.py`: durable, rolling 24-hour ceiling of 20 successful invitation issuances per (company, inviter) and 50 per company; uses existing committed `h05_audit` membership invitation issue events within SQLite `BEGIN IMMEDIATE` lock before token generation/delivery. Events count even after acceptance or expiry; failed delivery rolls back invitation + audit. Reject excess with frozen error envelope HTTP 409, `INVITE_RATE_LIMITED`, before sending/storing a fresh token. Other tenants/issuers cannot consume an unrelated actor's budget; company cap includes all issuers. No new migration, DB model or OpenAPI changes.
- `backend/tests/identity/test_auth_flows.py`: negative test on 20 distinct recipient addresses and denial of 21st; persist quota across new database engine; synthetic multiple-issuer company cap and denial across issuers; allow a distinct company; independent per-issuer limits; 24h window aging.
- `backend/app/modules/identity/README.md`: documented precise quota/409 behavior and corrected stale claim of no permission to edit H-04 test; Manager exception via merged PR #28 already handled two pinned migration invocations with all schema checks retained.

**Verification performed:** GitHub source read-back/compare confirms only these three allowed H-05 files changed from the Coordinator-reviewed SHA before this Developer report. Earlier owner's 47/47 successful Windows tests **apply only to old SHA** and cannot establish new behavior. **No Python/Windows test run of this change has been observed: NOT_TESTED, NOT PASS.** Request Windows Python 3.14.7/SQLite 3.50.4 `python -m pytest -v tests/identity tests/test_health.py` and `python -m pytest -v tests/db`; retain SHA, full stdout/stderr and both exit codes, then Coordinator re-review, independent QA and final Manager decision. PostgreSQL and production TLS/SMTP/concurrency remain DEFERRED/NOT_TESTED. PR #26 open/unmerged, H-06–H-08 untouched.
