# planner / REPORT

## 2026-11-14 — حسابیار (Hesabyar) — Proposed V1.0 Execution Plan

**Status:** PROPOSED / MANAGER_APPROVAL_REQUIRED — not approved, assigned, started, tested, or released.  
**Framework:** ChatGPT-Team-Framework 1.2.0 | **Repository:** `Ana0251/ChatGPT-Team-Test`  
**Source:** `.chatgpt-team/agents/manager/REPORT.md` (read directly), Planner prompt and role, `.chatgpt-team/PROJECT.md`, `.chatgpt-team/TASKS.json`, `.chatgpt-team/WAVES.json`, Planner INBOX/MEMORY.  
**Pre-write main HEAD:** `913cf98ac2e569a66df62a0042b1ca668973c3bb`; Planner REPORT prior blob SHA `8d8e651a3af73e3e93e851c37502ed18b5e4756a`.  
**Official ledger at intake:** 0 tasks, 0 approvals, 0 waves. This report changes neither official ledger. Manager report states no application source observed. All paths below are **proposals**, not claims that directories/files exist.

### 1. Scope, definitions and boundaries

**V1.0 release goal:** an operational Persian RTL multi-company financial accounting core: member-based authentication/authorization, company and fiscal year/period selection; group/کل/معین/تفصیلی chart of accounts; draft/posted/reversed journals with server-side double-entry controls; journal/daybook, general/subsidiary/detail ledgers, trial balance; responsive Jalali UI; audited sensitive operations; reproducible automated acceptance scenarios. No fake data presented as operational evidence.

**Proposed V1.1:** people, banking/cash/petty cash and integrated balanced receipts/payments. **V1.2:** balance sheet, P&L, management indicators/dashboard. **V1.3:** Excel/CSV imports/exports, polished PDF reports, expanded role/audit reporting. **Possible V1.0 exception:** basic CSV export of trial balance only if Manager explicitly prioritizes real workflow needs; preserve report correctness regardless. Do not silently expand V1.0.

**Accounting terms:** draft = mutable/unposted, posted = authoritative/immutable journal, reversal = separate balanced posted entry linked to original. Void/delete of posted entries prohibited. Fiscal close blocks posting/backdated mutation by API and DB-safe transaction checks. Only posted journals count toward ledger/trial balance. Soft-delete/archival of chart accounts is allowed only with hierarchy and usage controls. Define detail account policy before implementing schema (hierarchical detail vs floating detail links). No guessed Iranian regulatory/tax compliance in V1.0.

**Role abbreviations:** DEV=Developer; UX=UI/UX; QA=QA; COORD=Coordinator; PMA=PM Assistant; MGR=Manager. One accountable owner per task; QA separately validates developer output. `P0` release blocker; `P1` necessary UX/integration/operability; `P2` deferrable. `E` denotes proposed proof; no tests have run. Task IDs are proposal-only and MUST NOT be treated as registered IDs.

### 2. Architecture options and manager decision requests

**Recommended candidate (not approved):** modular monolith, TypeScript/React/Vite/Tailwind front end, Python/FastAPI backend, SQLAlchemy + Alembic with PostgreSQL, Pytest + httpx, Vitest/React Testing Library, Playwright E2E, OpenAPI-generated typed client, CI GitHub Actions; Recharts later when dashboards arrive. Package boundaries: identity/tenancy, fiscal, accounts, journals, reporting, audit. The monolith avoids premature distributed posting and distributed transaction complexity; modules must have explicit dependency boundaries.

**Alternatives to evaluate before approval:** (A) Django/DRF gives mature auth/admin but requires careful domain/business-rule organization; (B) NestJS/TypeScript unifies language but requires strong transactional ORM discipline. Decision comparison: implementation speed, financial-domain testability, migrations, authentication, maintenance and team familiarity. Stack is a managerial decision; no agent may bootstrap code before approval.

**Money:** baseline IRR integer rial units; DB `NUMERIC(20,0)` or justified `BIGINT` (range/overflow checked), Python `Decimal` for domain arithmetic, prohibit floating point. For future multicurrency choose `NUMERIC(20,4)` + per-currency scales only after policy approval; no casual scale mix. Validate amounts nonnegative, exactly one side per line (unless zero explicitly forbidden), total debit=credit, positive total, minimum two lines, account postability, no closed/future unauthorized date, full company/fiscal consistency. Amounts submitted as decimal strings, normalized on server. UI separators are display-only.

**Dates:** persist Gregorian `DATE`/UTC timestamps, show/input Jalali using a tested well-defined conversion library and a fixed IANA time-zone policy; conversion round-trip and boundaries are mandatory. Determine company-local cutoff for fiscal posting; avoid mixing timestamp and accounting date.

**Company isolation:** authenticated user-to-company membership; each command/query scopes `company_id` and role from server-verified membership; all relevant foreign keys and lookup constraints company-aware. Never trust header/URL/body company alone. Cross-company IDs respond with 404 or 403 under a consistent information-disclosure policy. Super-admin access requires an explicit separate approval. Consider PostgreSQL RLS defense-in-depth (not a replacement for application controls) after assessing operational complexity.

**Concurrency:** posting transaction locks journal and relevant period; one state transition, unique immutable voucher numbering with gap-policy decision, conflict response for stale/duplicate posting. Idempotency key per company/operation with bounded retention; uniqueness index and transactional enforcement. Isolation/locking strategy demonstrated in tests. Reversal atomic and separately linked; audit event committed with state transition (or durable outbox with tested delivery semantics).

**API:** `/api/v1`; OpenAPI contract freezes response/error shapes before UI integration. Consistent validation 400/422, auth 401/403, missing 404, conflict 409; never rely on UI-only rules. Pagination/order/filter stable and scoped. ISO canonical dates and decimal strings in API.

### 3. Granular proposed task register

All allowed paths are **exclusive edit scopes** for the named owner, with exceptions only through approved integration PRs. Test paths belong to the listed owner for initial authoring; QA evidence goes exclusively to `qa/` evidence paths and the QA agent's own report. **Each task contains owner, priority, wave, dependency, allowed files, deliverable, acceptance and evidence.**

| ID | Owner | Pri/Wave | Depends | Exclusive allowed paths (proposed) | Deliverable; acceptance criteria | Evidence expected |
|---|---|---|---|---|---|---|
| H-01 | MGR | P0/W0 | — | `.chatgpt-team/agents/manager/REPORT.md` | Approve scope, money/date rules, auth, stack, status model, numbering, task ownership; decision IDs recorded | Dated manager approval and exact version |
| H-02 | COORD | P0/W0 | H-01 | `docs/contracts/**`, `docs/architecture/**` | Module boundaries, OpenAPI baseline, ownership map; all consumers acknowledge version | Contract review + no-overlap checklist |
| H-03 | DEV | P0/W1 | H-01,H-02 | `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/core/config.py`, `backend/tests/test_health.py` | Run FastAPI service, health endpoint, deterministic env sample; test boot succeeds | CI backend boot/test log |
| H-04 | DEV | P0/W1 | H-03 | `backend/app/db/**`, `backend/alembic/**`, `backend/tests/db/**` | PostgreSQL connection/migration, reversible migration of empty schema, test DB isolation | Up/down migration log + schema diff |
| H-05 | DEV | P0/W1 | H-04 | `backend/app/modules/identity/**`, `backend/tests/identity/**` | Authentication, password hash policy, sessions/tokens, membership & role guard; unauthorized denied | API 401/403 + expiry tests |
| H-06 | DEV | P0/W1 | H-04,H-05 | `backend/app/modules/companies/**`, `backend/tests/companies/**` | Create/list/select company only via membership; scoped identifiers unique | Cross-company API negative tests |
| H-07 | DEV | P0/W1 | H-04,H-06 | `backend/app/modules/fiscal/**`, `backend/tests/fiscal/**` | Fiscal year + periods cannot overlap within company; open/close rules and year boundary | Overlap/closed-period concurrency tests |
| H-08 | DEV | P0/W1 | H-04,H-06 | `backend/app/core/money.py`, `backend/tests/core/test_money.py` | Decimal normalization, currency and range rules; floats rejected | Precision, overflow and invalid amount cases |
| H-09 | DEV | P0/W2 | H-06,H-07,H-08 | `backend/app/modules/accounts/**`, `backend/tests/accounts/**` | Group/کل/معین/تفصیلی hierarchy; scoped codes unique; no posting to non-leaves; used accounts not deletable | Duplicate/parent/type/company integrity tests |
| H-10 | DEV | P0/W2 | H-05,H-06 | `backend/app/modules/audit/**`, `backend/tests/audit/**` | Append-only actor/time/company/action audit trail; no secret leakage | Mutation audit/role denial tests |
| H-11 | DEV | P0/W2 | H-07,H-08,H-09,H-10 | `backend/app/modules/journals/models.py`, `backend/app/modules/journals/draft.py`, `backend/tests/journals/test_draft.py` | Draft journal CRUD; valid lines, account/company/period checked; drafts never appear in ledgers | Draft, invalid lines and cross-tenant tests |
| H-12 | DEV | P0/W3 | H-11 | `backend/app/modules/journals/posting.py`, `backend/tests/journals/test_posting.py` | Server-side exact balance, atomic posting, no overwrite of posted lines, role/period/number guards | Atomic rollback, imbalance and state tests |
| H-13 | DEV | P0/W3 | H-12 | `backend/app/modules/journals/reversal.py`, `backend/tests/journals/test_reversal.py` | Linked full reversal, no modifying original, prevention of duplicate reversals unless explicitly defined | Original + reversal zero-net reconciliation |
| H-14 | DEV | P0/W3 | H-12 | `backend/app/modules/journals/concurrency.py`, `backend/tests/journals/test_races.py` | Double-submit idempotency; concurrent post vs close protected; conflict responses deterministic | Parallel DB transaction tests |
| H-15 | DEV | P0/W4 | H-12,H-13 | `backend/app/modules/reports/ledger.py`, `backend/tests/reports/test_ledger.py` | Posted-only journal/daybook and 3 ledger levels; ordered movements, opening/closing/running balance, period filters | Golden ledger fixtures + SQL reconciliation |
| H-16 | DEV | P0/W4 | H-15 | `backend/app/modules/reports/trial_balance.py`, `backend/tests/reports/test_trial_balance.py` | Trial balance by company/year/date; debit/credit sums reconcile to journal; no draft impact | Trial-balance fixture and invariant checks |
| H-17 | UX | P1/W1 | H-01,H-02 | `design/tokens/**`, `design/specs/global/**` | Persian RTL tokens, light/dark, typography, numeric fields, accessibility and 360px responsive rules | Design audit checklist + annotated specs |
| H-18 | UX | P1/W1 | H-02,H-17 | `design/specs/identity/**`, `design/specs/company-period/**` | Login, company and period selector journeys; error/empty/loading/permission states | Screen flow and state matrix |
| H-19 | UX | P1/W2 | H-02,H-17 | `design/specs/accounts/**`, `design/specs/journals/**` | Chart editor + multi-line voucher UX; balancing feedback, confirmations and posted read-only states | Prototype spec + keyboard/focus checklist |
| H-20 | UX | P1/W3 | H-02,H-17 | `design/specs/reports/**`, `design/specs/accessibility/**` | Ledger/trial balance table, large-data paging, Persian/Jalali, printable view as optional browser print | Screens + a11y/responsive matrix |
| H-21 | DEV | P1/W2 | H-02,H-17 | `frontend/package.json`, `frontend/src/app/**`, `frontend/src/shared/**`, `frontend/tests/app/**` | Frontend shell, routing, RTL/theme/accessible primitives, typed contract; no business mock shown as real | Vitest accessibility/shell tests |
| H-22 | DEV | P1/W3 | H-18,H-21,H-05,H-06,H-07 | `frontend/src/features/auth/**`, `frontend/src/features/company-period/**`, `frontend/tests/features/auth/**` | Auth and tenant/period flows integrated; expired access handled safely | RTL/authorization/browser E2E evidence |
| H-23 | DEV | P1/W3 | H-19,H-21,H-09 | `frontend/src/features/accounts/**`, `frontend/tests/features/accounts/**` | Account hierarchy CRUD, validation and duplicate errors integrated | UI/API integration test |
| H-24 | DEV | P0/W4 | H-19,H-21,H-11,H-12,H-13,H-14 | `frontend/src/features/journals/**`, `frontend/tests/features/journals/**` | Draft/edit/post/reverse; line totals display; posted immutability; double click doesn't double-post | Multi-step browser financial scenario |
| H-25 | DEV | P1/W5 | H-20,H-21,H-15,H-16 | `frontend/src/features/reports/**`, `frontend/tests/features/reports/**` | Journal/ledger/trial balance usable on desktop/mobile, filters and exact decimal formatting | Filter/pagination/total E2E |
| H-26 | QA | P0/W2–W5 | H-05 onward per module | `qa/testplans/**`, `qa/fixtures/**`, `qa/evidence/**`, `.chatgpt-team/agents/qa/REPORT.md` | Independent threat/accounting test plan, execute each delivered module against real database; defects with reproducible steps | Timestamped CI logs, case IDs, HTTP traces/redactions |
| H-27 | COORD | P0/W5 | H-12,H-14,H-16,H-22,H-23,H-24,H-25,H-26 | `docs/integration/**`, `.chatgpt-team/agents/coordinator/REPORT.md` | Confirm contract compatibility, merge order, review ownership and CI gates; NO unapproved source edits | Reviewed PR references and SHA matrix |
| H-28 | DEV | P0/W5 | H-03,H-04,H-21,H-27 | `infra/**`, `.github/workflows/**`, `docs/runbook/**` | Reproducible env/bootstrap, DB migration, seed **synthetic** fixtures, backup/restore instructions, CI gates | Fresh-install, migration & restore drill |
| H-29 | QA | P0/W6 | H-16,H-24,H-25,H-27,H-28 | `qa/evidence/release-v1/**`, `.chatgpt-team/agents/qa/REPORT.md` | End-to-end financial, isolation, concurrency, Jalali, responsive/accessibility regression; no critical blocker | Evidence per case, failed/pass counts & environment SHA |
| H-30 | MGR | P0/W6 | H-29 | `.chatgpt-team/agents/manager/REPORT.md` | Accept/reject V1.0 from evidenced release gate, document remaining known limitations | Signed decision referring to build/test SHAs |

**Ownership qualifier:** H-01 and H-30 are *manager decision gates*, not executable assignments by Planner. H-26 testing starts as soon as first code is actually available, despite its early planning placement. UX work is primarily specification/prototype work, **not modification of Developer code**. QA must not silently patch production code. Coordinator owns integration documentation; merge authority follows manager-approved workflow. PM Assistant registers approved tasks/waves only *after* manager approval. Reports of other agents are not modified by Planner.

### 4. Execution waves / dependencies

| Wave | Entry gate | Parallel safe lanes | Exit evidence |
|---|---|---|---|
| W0 Decision & contracts | Manager intake reviewed | H-01 then H-02 (sequential); QA may read only | Approved scope/stack/roles, signed contracts, file scopes |
| W1 Foundation | W0 approved | DEV H-03→H-04→(H-05,H-08)→H-06→H-07; UX H-17→H-18 | DB migrations, auth/tenant fiscal tests; UX specs |
| W2 Domain + interface | W1 foundation | DEV H-09, H-10; UX H-19; DEV H-21 after H-17; QA H-26 starts | Accounts hierarchy, audit and UI shell verified |
| W3 Posting + operational views | W2 prerequisites | DEV H-11→H-12→(H-13,H-14); UX H-20; DEV H-22/H-23 (separate feature paths) | Atomic posted journal, reversal/race tests, user flows |
| W4 Financial queries + journal screen | W3 posting | DEV H-15→H-16; DEV H-24 after posting; QA adversarial accounting checks | Cross-check posted totals and journal UI |
| W5 Reporting + integration | W4 ledger stable | DEV H-25; QA H-26; COORD H-27 after feature verification; DEV H-28 | End-to-end reports + reproducible deployment/CI |
| W6 QA release gate | All V1 paths integrated | QA H-29, then MGR H-30 | Reconciled test dossier and explicit release decision |

**Proposed critical path:** H-01→H-02→H-03→H-04→H-05→H-06→H-07/H-08→H-09→H-11→H-12→H-13→H-15→H-16→H-25→H-27→H-28→H-29→H-30. H-14 concurrent-posting guard is a **mandatory join gate**, not optional merely because it can be worked in parallel. Likewise H-24 and security QA join before release. Calendar duration and scheduling cannot be inferred without estimates/capacity; this is a **logical** critical path, not an invented dated Gantt.

**Wave policy:** no task starts without manager approval, assigned owner, recorded dependencies and file scopes. No wave marked done on proposals alone. If a prerequisite changes, Coordinator refreshes contract compatibility and manager/PMA revise approved ledger; never bypass blockers.

### 5. Explicit no-conflict editing protocol

1. UX owns **only `design/**`**. Deliver design tokens, user journeys and annotated screens; does **not** edit `frontend/**`, `backend/**`, `docs/contracts/**` or other agent reports.
2. DEV owns **`backend/**`, `frontend/**`, `infra/**`, `.github/workflows/**`, and `docs/runbook/**`**, within per-task scopes above; separate PRs per module/screen. H-03/H-04 baseline config PRs precede feature PRs. No simultaneous changes to `frontend/src/app/**` by several packages.
3. COORD owns **`docs/contracts/**`, `docs/architecture/**`, `docs/integration/**`** and its own report; changes to shared API contracts are proposed with version/change log and reviewed by DEV+UX before a consumer changes code.
4. QA owns **`qa/**`** and its own report. QA files are isolated from DEV's `backend/tests/**` and `frontend/tests/**`. QA may request changes but does not commit to other agent's paths.
5. MGR alone decides scope/approvals and signs off; PMA alone registers approved `TASKS.json`/`WAVES.json`. Planner edits only `.chatgpt-team/agents/planner/REPORT.md` in this handoff.
6. Every PR records task ID, base SHA, file list, contract revision, tests, rollback and reviewer. Enforce path checks/CI, compare changed paths against task ownership; branch `feature/h-XX-short-name` after approval; no direct risky code write to main. Before write: refetch HEAD/blob SHA and avoid overwriting remote changes. Integrator resolves any shared-client generation/lockfile change serially.
7. Contract-before-implementation gate: UX may produce independent specs while DEV domain progresses; frontend *integration* requires frozen routes, request/response schemas and stable errors. Shared tokens are communicated via a reviewed spec, not live simultaneous edits.

### 6. Mandatory accounting invariants and reproducible acceptance fixtures

**Fixture F1 (all amounts IRR; company A, open period):** Initial opening-style balanced voucher: Dr cash 1,000,000 / Cr capital 1,000,000. Voucher 2: Dr expense 200,000 / Cr cash 200,000. Trial balance by posting-side movements: debits **1,200,000** and credits **1,200,000**. Ending balances: cash **800,000 debit**, expense **200,000 debit**, capital **1,000,000 credit**. Net debit balances = net credit balances = **1,000,000**. This fixture is a simple pedagogical chart; opening balance presentation policy still requires approval. Ledger cash running balance: +1,000,000 then -200,000 = +800,000. Draft Dr expense 9,999 / Cr cash 9,999 should not change results until posting.

**Fixture F2 reversal:** Fully reverse voucher 2 with Dr cash 200,000 / Cr expense 200,000; original preserved; resulting cash 1,000,000 debit, expense 0, capital 1,000,000 credit; movement totals each side **1,400,000**, ending debit/credit balances each **1,000,000**. No inconsistent partial reversal.

**Fixture F3 isolation:** In company B, create account and voucher with deliberately overlapping human account codes and numeric amounts. A member of A only cannot list, fetch, update, post, reverse or report B data, including guessed IDs and exporting filters. A user with memberships in both sees only selected authorized company and cannot mix lines from A and B. Run directly via API, not just hidden UI.

**Negative/edge gates:** unbalanced 100/99 rejected without row or audit inconsistency; zero/negative/overprecision/floating submission rejected according to policy; duplicate account code in same company fails but identical codes in different company succeed; posting to group/disabled account fails; fiscal overlap fails; posting closed period fails even on race with closure; double post generates one posted voucher; posted edit/delete fails; unauthorized reversal denied; POST retries idempotent; Jalali leap/boundary and round-trip; hidden/disabled buttons do not replace server controls; paginated ledger sum agrees with unpaginated canonical totals; empty account and zero movement report, time-zone rollover, migration/restore. Verify no cross-company event leakage in audit.

**Testing tiers and actual evidence:** unit tests for money/calendar/domain; PostgreSQL integration tests for FK/constraints/locking/rollback; endpoint tests for 401/403/404/409 and IDOR; frontend component tests for RTL/keyboard/errors; Playwright multi-company user journeys; independent QA acceptance with immutable test logs, fixture version, build/commit SHA and pass/fail details. Test coverage numbers should be documented from actual CI, not fabricated. Database concurrency tests must use real PostgreSQL, not SQLite substitutes. All synthetic data must be clearly marked.

**V1 acceptance gate (all required):** migration clean-install works; authenticated authorized flow creates company/year/accounts/draft, posts balanced vouchers exactly once, reverses appropriately; ledgers/trial balance reconcile F1/F2; A/B isolation tests pass; period close + concurrency/immutability tests pass; keyboard-readable Persian UI with explicit errors, responsive 360px and standard desktop; documented installation/backup restore; QA release dossier has zero unresolved critical/high security or financial integrity defects; explicit Manager sign-off.

### 7. Risk register and mitigation

| Risk | Level | Mitigation / owner |
|---|---|---|
| Cross-tenant leak/IDOR | Critical | DEV scoped membership middleware, compound FK; QA negative API suite; MGR release blocker |
| Unbalanced/partial/duplicate posting | Critical | DEV single DB transaction, Decimal, locking+idempotency; QA race and rollback cases |
| Ledger totals drift from source journals | Critical | DEV one canonical posted-lines query semantics, golden fixtures; QA independent recomputation |
| Ambiguous detail-account hierarchy | High | MGR approves detail policy in H-01; COORD contract freeze |
| Fiscal closure vs late backdate | High | DEV transactional period checks, QA concurrent posting/closing |
| Concurrent work causes contract/file collision | High | COORD sole contract editor and branch/PR path gate |
| Incorrect Jalali dates or Rial representation | High | MGR currency/timezone convention; UX input spec; DEV round trips; QA boundaries |
| Overgrown V1 scope | High | MGR version boundary and change control; defer treasury/dashboard |
| Security/session secrets in logs | High | DEV secret management and audit redaction; QA role/session tests |
| No reproducible test environment | High | DEV migration/CI seed + QA real DB and restore evidence |

### 8. Decisions explicitly reserved for Manager

**D-01:** approve V1.0 scope and proposed V1.1–V1.3 cut; CSV in V1.0 yes/no.  
**D-02:** choose stack: recommended FastAPI+React+PostgreSQL modular monolith vs Django/DRF vs NestJS, with team capability considered.  
**D-03:** authorize initial auth method (email/password internal, MFA/admin policy), RBAC roles (owner/admin/accountant/viewer), company membership invitation and super-admin exclusions.  
**D-04:** money: IRR only, integer rial precision/range; whether future multicurrency is explicitly out-of-scope.  
**D-05:** fiscal policy: Iranian Jalali year model converted to Gregorian storage, local TZ (e.g. Asia/Tehran for operational account dates), posting-date and close permissions.  
**D-06:** chart account detail linking/leaf postability, account numbering uniqueness, fiscal numbering and whether gaps allowed.  
**D-07:** posting/reversal transitions, audit retention and legal/regulatory constraints (no unsupported compliance claim).  
**D-08:** approve exclusive path ownership, PR/review gates, schema contract process and who has merge authority.  
**D-09:** define release operational target (on-prem/cloud), backups, privacy/data retention, and initial load/scale targets so performance gates can be quantified.

**Proposed manager response:** APPROVE / REQUEST_CHANGES by decision IDs; do not register tasks/waves without recorded approval. Manager may select a smaller minimum slice only with revalidated accounting/tenant integrity. PM Assistant then registers approved waves/tasks from this proposal; Coordinator validates sequencing and collisions; DEV and UX work only on individually approved packages; QA independently tests. This document is a planning handoff, not authorization to code.

### 9. Handoff & integrity statement

Planner read role instructions and the Manager report directly from GitHub and only authored this report under its own directory. Neither `.chatgpt-team/TASKS.json` nor `.chatgpt-team/WAVES.json` was changed; zero implementation tasks were executed, no code or test results were manufactured. Await manager decision before task registration or execution.
