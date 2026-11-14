# manager / REPORT

## 2026-11-14 — Hesabyar (حسابیار) — Project Intake & Planner Handoff

**Status:** ANALYSIS_REQUESTED / PLANNING_PENDING. This is a manager intake report, NOT an approved task plan, a test result, or a development completion claim.

**Repository:** Ana0251/ChatGPT-Team-Test  
**Framework:** ChatGPT-Team-Framework 1.2.0  
**Verified main HEAD before planning:** `308a282505bb9360e299f56260ed7cc682f5f726` (must recheck before any future write).  
**Initial authoritative ledgers:** `.chatgpt-team/TASKS.json` = 0 tasks, 0 approvals; `.chatgpt-team/WAVES.json` = 0 waves.  
**Existing application source:** None observed in root; repository contains framework files only.  
**Source:** User's project start brief on 2026-11-14 in the manager conversation. Manager and Planner instructions read directly through the connected GitHub tool.

### Product objective and target releases

Build a real, testable, extensible Persian/RTL multi-company accounting web application. The requested capability set includes company/fiscal period management, chart of accounts, double-entry journals, ledgers and trial balance, treasury, people, financial statements, management dashboards, data import/export, users/roles/audit trail, Jalali dates and responsive light/dark UI.

**V1 proposed deliverable (functional accounting core):**
1. Minimum company, fiscal year/period, authentication and company-scoped authorization needed to operate without cross-company exposure.
2. Chart of accounts: group, general ledger (کل), subsidiary (معین), detail (تفصیلی); hierarchical integrity, scoped unique codes and lifecycle restrictions.
3. Double-entry journal: draft creation/edit, validation, posting/finalization, immutable posted lines, corrective/reversal entries, closed-period restrictions, auditable sensitive events.
4. Journal, general/subsidiary/detail ledgers, account movements, trial balance (opening, debit, credit and closing columns as applicable).
5. Operational Persian RTL screens for the above, company/period selector, Jalali presentation, accessible and responsive forms, user-facing financial validation errors.
6. Repeatable backend, frontend, and end-to-end accounting scenario tests with sample data and expected outcomes.

**After V1, proposed sequencing (not yet approved as tasks):**
- V1.1: persons, bank/cash/petty cash, receipts/payments with balanced accounting integration.
- V1.2: balance sheet, profit/loss, management indicators and dashboard.
- V1.3: Excel/CSV import/export and PDF reports, expanded permissions and audit review, UI polish; consider import/export needs earlier if Planner finds a justified operational dependency.
Version numbering and exact scope must be validated by Planner and manager against dependencies.

### Architectural constraints / decisions to analyze, not yet approved

- Candidate stack: React + TypeScript + Tailwind CSS; Python + FastAPI; PostgreSQL; Recharts; Pytest + Vitest. Planner should identify technical decision points and alternatives rather than assuming final stack approval.
- Money: no binary floating-point for stored monetary amounts; choose a documented precision/scale policy by currency, use Python Decimal and PostgreSQL NUMERIC (or justified integer subunits), enforce debit-credit equality server-side and through transactional writes.
- Posting must be atomic, idempotency/concurrency-aware and guarded by current company and fiscal-period state. No silent change/delete of posted journals; preserve original and linked reversal/correction.
- Company-level isolation by authenticated membership, not only a client selector. Add adversarial tests for cross-tenant reads/writes, direct-object references, insufficient permissions, closed periods, and duplicate or concurrent posting.
- Account hierarchy and fiscal year/period constraints must precede posting and ledger correctness; agree posting statuses and audit trail semantics.
- Persist canonical dates and reliably convert Jalali for presentation/input; specify currency (IRR baseline unless revised) and rounding configuration.
- Ledger queries and financial statements must have a reproducible accounting definition; reports must reconcile to posted journals.
- No invented evidence: test PASS, PR, commit, or task completion is valid only with verifiable artifacts/links.
- No direct risky code edits on main. Code via scoped branch/PR, with explicit file ownership and integration review.

### Provisional dependency outline (Planner must verify and refine)

Company/identity/access + fiscal calendar + schema/migrations + monetary policy + account hierarchy -> journal validations and transactional posting -> ledger and trial balance services -> operational UI integration -> reconciled scenario and security tests -> QA evidence and acceptance.

UI/UX research, design tokens, Persian interaction specs and page mockups can progress in parallel with API/domain design **after interface contracts and file boundaries are agreed**. Do not declare UI implementation independent of APIs prematurely. Coordinator integrates branches and contracts; QA validates actual runnable behavior and financial invariants.

### Required Planner output

Provide a concrete, small-grained, versioned task proposal (without directly editing the authoritative task/wave ledgers): for each proposed task specify role/owner, deliverable, acceptance criteria, allowed file paths, dependencies, risk, test evidence and candidate execution wave. Identify critical path and safe parallelism (UI/UX vs Developer), cross-company access rules, currency/date conventions, transaction correctness, schema, example financial test cases (including expected balances), and milestones for V1 first. Flag product decisions needing manager approval; escalate only genuinely high-risk, major-scope or public-release decisions to user. Inspect current repo state and all own role files first; write Planner's proposal to `.chatgpt-team/agents/planner/REPORT.md` only. Return to manager for approval. No task ledger mutations, other-agent writes, coding, or unapproved execution.

### Coordination sequence

1. User visits independent **Planner** conversation and submits the handoff provided by manager.
2. Planner checks official repo state and publishes its proposal under its own report.
3. User returns to manager conversation with report link; manager evaluates dependencies, scope, owners, and architecture, approves a specific plan and records approvals/decisions.
4. Only then PM Assistant batch-registers approved tasks/waves. Subsequently assign UI/UX and Developer safe parallel packages; Coordinator reviews integration; QA submits runnable test evidence; PM Assistant prepares status and next-wave proposals.

**No task, wave, code implementation, architecture finalization, or test execution is claimed here.**

## 2026-11-14 — Manager Decision: APP-HESABYAR-V1-20261114-001

**Result:** Planner proposal accepted with explicit amendments and registered as an approval (not tasks) in authoritative `.chatgpt-team/TASKS.json`. Complete decision text stored in `.chatgpt-team/DECISIONS.md`. Planner proposal source blob SHA: `07094c8ef89978c1751d021d36b25a5feece81f4`.

**Approved:** 30 proposed items H-01..H-30, 7 proposed waves W0..W6; FastAPI/React/PostgreSQL modular monolith, IRR integer policy, Jalali presentation with Asia/Tehran accounting calendar, tenant-scoped access, company-owned hierarchical accounts, atomic/auditable posting. Scope V1 operational core then V1.1 treasury, V1.2 financial reporting/dashboard, V1.3 import/export. No public deployment approval.

**Mandatory registration corrections:** early CI in H-03/H-21; H-28 for complete CI and recovery; Alembic additive revisions serialized; draft may be incomplete but posting may not; explicitly scoped frontend config/client ownership; cross-tenant, concurrency, reversal and fiscal closure QA gates, code PR reviews and protection of main before code merges. Full wording in `DECISIONS.md`.

**Next conversation:** PM Assistant. Read recorded approval and Planner report, batch-register tasks and waves without independently changing scope or priorities, report exact commit and counts. No agent has been activated by this manager conversation. No coding/tests have started.
