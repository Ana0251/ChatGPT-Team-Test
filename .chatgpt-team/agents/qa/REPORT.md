# qa / REPORT

## 2026-11-14 — H-18 independent documentation QA — PR #17

- **Result:** PASS LIMITED — documentation/specification review ONLY. This is not a runtime/browser/accessibility/security PASS, nor formal acceptance or merge authorization.
- **Framework:** 1.3.0. Legacy route: UI/UX owner → Coordinator → independent QA → Manager. Coordinator review: [PR #17 comment 6879398410](https://github.com/Ana0251/ChatGPT-Team-Test/pull/17#issuecomment-6879398410), PASS LIMITED.
- **Reviewed PR HEAD:** `8730866fde49dd61c7f66b85937d020771875e51` (open, unmerged before this QA report write). **Frozen contract** `docs/contracts/openapi.yaml`, version `1.0.0-rc.3`, blob `98d34e7bd7b4551c0f429ea5e388781060ceaf63`.
- **Authorized work:** H-18 `start_authorized=true`, dependencies H-02/H-17 `COMPLETED`, W1 entry authorized. H-18 ledger remains `AUTHORIZED_NOT_STARTED`; no ledger/state change by QA. H-26 not started.

### Evidence read (GitHub contents, static/manual comparison)
1. `design/specs/identity/AUTH_AND_INVITATIONS.md` blob `9cbad5b4de738a854320502633f254aa69f32ec8`.
2. `design/specs/identity/SESSION_STATES.md` blob `f7b52bc764d839782a74d4ba064c13c8fdf1643c`.
3. `design/specs/company-period/COMPANY_FISCAL_SELECTION.md` blob `3a07553adb7762803023906ab9bf87ebf1f3bf39`.
4. `design/specs/company-period/STATE_MATRIX_AND_REVIEW.md` blob `42009cf5aace6b14bf34cec30eef9592e7e3f7b2`.
5. Main: QA role/prompt 1.3.0, TASKS/WAVES/DECISIONS, H-17 `DESIGN_SYSTEM.md` and `REVIEW_CHECKLIST.md`, frozen OpenAPI, PR #17 changed paths and Coordinator review.

### Acceptance traceability (document inspection results)
- **ID-01–ID-08 (8/8 SPECIFIED):** internal email/password login, CSRF pre-auth and renewal, `/auth/me`, logout, 401/403/422, expiry, provisioning of first owner, invitations for new/existing users, pending invite status and owner-only company-scoped owner invitations. OpenAPI methods/response codes and CSRF/security constraints match at documented level.
- **CP-01–CP-06 (6/6 SPECIFIED):** membership-scoped companies, company-local role, explicit switch/clear context, no companies/years/periods, open/closed period, Gregorian exclusive end to Jalali inclusive previous calendar day. Relevant frozen API schemas and paths were inspected.
- **UI-01–UI-04 (4/4 SPECIFIED):** Persian RTL with LTR isolation, light/dark tokens, single-column 360px / 16px padding / >=44px targets, keyboard/focus/screen-reader/reflow/200% zoom and reduced-motion requirements referenced to H-17.
- **GOV-01 (1/1 SPECIFIED):** prior to this QA report commit, PR #17 changed four H-18 design files and the UI/UX owner's role report only. No edits to `frontend/**`, `backend/**`, frozen OpenAPI or task/wave ledgers. This QA role report is an additional, separately authorized report path.
- **Cross-screen matrix:** login, session, invitation, activation, company, fiscal year, fiscal period; Loading/Empty/Error/Permission Denied/Success cases defined. `SPECIFIED` is not a tested PASS.

### Follow-up items (not blocking documentation-only acceptance)
- Implement company-switch cancellation / request-generation gating and company-keyed caches so late in-flight responses cannot restore previous-company data.
- Prove invitation/setup token handling never creates token-bearing URLs, browser history, logs or persistent storage; use secure manual entry or compliant delivery. Verify error messages don't reveal membership.
- Execute future UI/browser at 360/390/600/1024, light/dark, 200% zoom, keyboard/focus, screen reader, reduced motion, localization and actual error/empty/loading/permission states.
- Independently test actual session/CSRF/401/403/404/409/422, role restrictions, invitation lifecycle and tenant isolation on implemented server. Verify no mutation retry after uncertain network response.

### Limitations and disposition
- **Documentation completeness: PASS LIMITED** (manual static GitHub file/contract cross-check; 19/19 design scenarios are specified).
- **Browser/rendering/360px/screenshots, two-theme actual contrast, keyboard/screen-reader, runtime API, actual auth/CSRF/tenant/security tests: NOT_TESTED.** No executable commands were run, and no runtime PASS is claimed.
- This recommendation applies to the four exact document blobs and the pre-QA PR head above. Any substantive design/API change requires re-review. Coordinator's earlier limited review is not treated as independent QA evidence.
- **Manager decision required:** accept design specification scope only or request further changes; keep PR #17 open, do not mark H-18 COMPLETED or merge based on this report alone.

## 2026-11-14 — H-04 independent QA review / PR #18

**Disposition: PASS LIMITED (manager-approved local SQLite H-04 baseline only); recommend limited acceptance for Manager decision, not completion/merge.** Independent *source and owner-evidence review* performed via GitHub connector; **QA did NOT run Windows/Pytest/Alembic commands**. Framework 1.3.0 legacy Coordinator-required route; Coordinator PASS LIMITED and handoff: [comment 6880332388](https://github.com/Ana0251/ChatGPT-Team-Test/pull/18#issuecomment-6880332388). Owner-executed tests transcribed by Manager: [comment 6880269744](https://github.com/Ana0251/ChatGPT-Team-Test/pull/18#issuecomment-6880269744). Scope-specific QA review of exact **code SHA** `c6b3c20da04ac5a381869f2ee10eabc2af20744e`; review does not rely on later report commits as test code.

### Governance and file scope
- Read on `main`: QA prompt and role (Framework 1.3.0), TASKS, WAVES, DECISIONS; H-04 `AUTHORIZED_NOT_STARTED`, `start_authorized=true`, dependency H-03 `COMPLETED`; W1 `AUTHORIZED_NOT_STARTED` / `entry_authorized=true`; H-26 `NOT_STARTED` and not authorized. Preserve all statuses.
- Manager temporary local SQLite exception `APP-HESABYAR-DB-LOCAL-SQLITE-20261114-001`; manual validation policy `APP-HESABYAR-MANUAL-VALIDATION-20261114-001`. This is not approval of a production engine or PostgreSQL equivalence.
- PR before this report changed only `backend/app/db/engine.py`, `backend/app/db/money.py`, `backend/alembic/{README.md,alembic.ini,env.py,versions/h-04_0001_baseline.py}`, `backend/tests/db/{test_sqlite_storage.py,test_migrations.py}`, `backend/pyproject.toml`, and developer-owned `.chatgpt-team/agents/developer/REPORT.md`. All are approved H-04 or role-report paths. No other owners' code, API, TASKS, WAVES, decisions, .db or credentials changed in PR; QA adds only its authorized own report.
- Code examined directly at exact ref; blob SHA: engine `ab346ded6e625125a347e5bcde1ac6e0258ac6b9`, money `7d69c1fdef53e32697c9012b59a8a8ed21d7a34a`, storage tests `bf397b25a3eee889ee8eec822016dfbbf27d975d`, migration tests `d857ffc39d681f31f77833025d827fc3675acd86`, Alembic env `490647c2995006af912c9686f0179a9ed2b8d6e6`, revision `b6788194eadbf0f42ffd1bee5064c875d0cc923c`.

### Independent technical findings (STATIC CODE REVIEW / OWNER EVIDENCE REVIEW; not QA-executed runtime)
1. **File-backed SQLite:** `create_sqlite_engine` requires explicit URL, SQLite dialect, nonempty absolute path, existing parent, and file rather than a directory; denies `:memory:`, relative, `file:` URI and query-mode URLs. Tests include valid file-backed case and invalid URL/parent/directory cases. **Code coverage inspection: SATISFIED.** No assertion that every conceivable OS/filesystem edge case was runtime-tested.
2. **Foreign keys and isolation:** DBAPI `connect` event sets and reads `PRAGMA foreign_keys=ON`, raising if not 1; tests assert separate disposable DB files/schemas, FK violation rejection, and a newly opened physical connection after engine disposal. **Code coverage inspection: SATISFIED.** This does not prove actual tenant isolation or all externally created connections.
3. **Exact IRR:** `ExactRial` uses canonical 1–20 digit nonnegative integer string regex, SQLite `TEXT` storage, Python `Decimal` result; prohibits bool/float, fraction, negative, overflow, noncanonical leading-zero amounts and exponent forms including `Decimal('1E+3')`, `Decimal('0E+3')`, `Decimal('1.0')`. `Decimal('1000')` accepted. Tests verify 20-digit value exactly, stored typeof=text, account code `000001`, rejected inserts leave count 0. **Adapter-level code inspection: SATISFIED.** This does not prove arbitrary raw SQL bypass resistance or PostgreSQL NUMERIC(20,0).
4. **Alembic:** Only infrastructure `h04_schema_baseline` created/dropped; two columns `id INTEGER PK NOT NULL`, `label TEXT NOT NULL`, no foreign/unique/check constraints. Fresh inspector snapshots include column names/types/nullability/PK, PK columns, FK/unique/check arrays; first and second upgrades compared equal, table absent on downgrade, separate DB untouched. Live NULL-label rejection included. Alembic version tracking table expected to remain after downgrade. **Code inspection: SATISFIED** for this minimal baseline, not business tables.
5. **Owner-run evidence (not QA-run):** Windows PowerShell isolated worktree at guarded code SHA; Python 3.14.7, SQLite 3.50.4, SQLAlchemy 2.1.8, Alembic 1.20.1, Pytest 9.2.0. `python -m pytest -v tests/db`: **24 passed, 3 warnings, 0.93s, exit 0**, per owner-provided Manager-transcribed PR evidence. Alembic CLI `upgrade head` → `downgrade base` → `upgrade head`: each **exit 0**. Before tables `[]`, upgrades `['alembic_version','h04_schema_baseline']`, downgrade `['alembic_version']`; schema column/PK/FK/unique/check snapshots identical across both upgrades; PRAGMA foreign_keys=1 in all four observed snapshots. DB under `D:/ChatGPT-Team-Test-H04-data/h04-<timestamp>.db`, outside repository. Evidence matches source expectations and is **accepted as OWNER-EXECUTED, QA-INDEPENDENTLY-REVIEWED**, not independently rerun or authenticated by QA.
6. **Warnings:** three Alembic `DeprecationWarning` concerning missing `path_separator` in `alembic.ini`, legacy splitting; nonblocking local H-04 cleanup suggested before tooling upgrade. Not warning-free PASS.

### Boundary, NOT_TESTED and decision
**QA runtime execution on Windows: NOT_TESTED.** PostgreSQL native NUMERIC(20,0), row locking, concurrent close/post/financial races, true financial/accounting correctness, HTTP/API, real cross-company security/tenant authorization, raw SQL bypass resistance, production/release DB suitability, backup/restore and recovery: **DEFERRED / NOT_TESTED**. No global feature/security/release PASS. Evidence is manually executed by owner, not by QA/Coordinator/Manager. The minimal Alembic schema is not a financial production schema.

**Recommendation:** Manager may accept **PASS LIMITED for the H-04 local SQLite infrastructure gate**, with warning follow-up and deferred later-engine/tenancy/security tests explicitly retained; Manager alone decides completion/merge. Keep PR #18 open and ledger H-04 unchanged until manager decision. H-26 or any other task NOT_STARTED; no W1 exit or H-05 authorization. If SHA or code scope changes materially, re-review.
