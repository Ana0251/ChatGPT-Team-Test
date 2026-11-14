# manager / HANDOFF

## 2026-11-14 — PM Assistant to register manager authorization for H-04/H-18

**Current merged evidence:** PM Assistant PR #11 merged into protected main as `702d71fac22ac2608b6df04fb71dfdae80498100`; H-03 `COMPLETED` with real Windows 3/3 Pytest and live health HTTP 200, nonblocking deprecation warning, QA/DB/auth/finance NOT_TESTED. H-17 `COMPLETED` design documentation only, runtime UX/accessibility NOT_TESTED. W1 `AUTHORIZED_NOT_STARTED`, `entry_authorized=true`. H-02 contract frozen OpenAPI 1.0.0-rc.3 SHA `98d34e7bd7b4551c0f429ea5e388781060ceaf63`.

**Manager decision:** `APP-HESABYAR-W1-H04-H18-ENTRY-20261114-001` in DECISIONS.md/TASKS approvals after governance PR merge; only H-04 Developer and H-18 UI/UX are now authorized for next staged start after PM Assistant ledger sync. PM Assistant must read its own role prompt, TASKS/WAVES, DECISIONS, Manager report/HANDOFF and project files first. New branch+PR only. Change exactly H-04/H-18 from `NOT_STARTED` to `AUTHORIZED_NOT_STARTED` and `start_authorized=true`; preserve 30 tasks, 7 waves, W1 status, all other task/wave auth statuses, and manager approvals. Record decision reference only where appropriate. Do not auto-start agents or run task implementation.

**H-04 Developer:** backend/app/db/**, backend/alembic/**, backend/tests/db/** plus own REPORT only. Real PostgreSQL connection/migration up/down/up + schema diff, isolated test DB, no committed secrets or customer data. Watch dependency ownership: `backend/pyproject.toml` and shared `backend/app/core/config.py` **not** allowed H-04; if persisted Alembic/SQLAlchemy/psycopg deps/common settings necessary, Developer asks Coordinator/Manager for a scoped approval BEFORE touching these. No H-05 identity/H-06 companies, etc. QA not waived. Real user manual test commands/versions/outputs and exact SHA required, no GitHub Actions gate.

**H-18 UI/UX:** only design/specs/identity/** and design/specs/company-period/** plus own report; login, invitation, memberships, company & period selection flows, permission/session recovery, error/loading/empty/state matrix. Frozen OpenAPI/approved H-17 context. No frontend/backend or H-19 implementation. Browser UX runtime not tested in documentation task.

After PM Assistant PR merged and Manager verifies main, user separately sends task prompts to Developer/UIUX. H-05/H-06/H-07/H-08 and W2-W6 stay locked; W1 not completed.
