# H-02 — File ownership, review gates and zero-overlap checklist
Revision: 1.0.0-rc.3 | Status: proposed; not yet consumer acknowledged

## Exclusive scopes and future task sequencing
Coordinator (H-02 only): docs/contracts/** and docs/architecture/**. Own agent's report: .chatgpt-team/agents/coordinator/REPORT.md (role-specific reporting exception, no other agent report). H-27 docs/integration/** is NOT authorized.
UI/UX: design/** only, during individually approved H-17..H-20. They may specify interactions/errors but must not edit frontend/**, backend/** or contracts.
Developer: only assigned per-task backend/**, frontend/**, infra/**, .github/workflows/**, docs/runbook/** paths, in authorized later waves. H-21 exclusively owns frontend package.json, generated typed API client, frontend shared shell/config and lockfiles; UX consumes/reviews schemas, not code.
QA: qa/** and its own report; QA independently validates, never silently modifies application code. PM Assistant is exclusive editor of formal ledgers TASKS.json/WAVES.json when manager approves. Manager owns approvals, merge/release gates and manager report.

## Contract governance
1. One PR per authorized task; branch feature/h-XX-short-name; base main and record latest base SHA. No direct main writes. Check task.start_authorized, wave.entry_authorized, dependencies, allowed paths and existing file blob SHA BEFORE writes.
2. H-02 OpenAPI is the proposed source-of-truth. Before frontend integration, Developer and UI/UX each acknowledge the exact contract version and SHA in PR review or documented comment; Coordinator records both and Manager authorizes freeze. This PR cannot self-approve.
3. A change to an endpoint, money/date semantics, permission, error code or schema needs contract change PR by Coordinator, changelog, compatibility assessment, Developer+UX review, Manager approval where scope/security semantics change; regenerate typed client only through authorized H-21 owner and separate PR. Do not quietly drift generated client.
4. API contract version 1.0.0-rc.3 is prerelease; immutable tagged baseline after approval. Patch: docs/additive clarification/non-behavioral fix. Minor: backwards-compatible optional field/endpoint, with reviewer approvals. Major: removing/renaming required fields, changing defaults/permissions/error semantics or URLs; use /api/v2 for breaking public HTTP changes. No breaking edits under /api/v1 after freeze without versioned migration.
5. PR checklist: task/wave/auth IDs, base SHA, changed files, module/owner map, API diff and examples, F1/F2/F3 implications, compatibility with typed client, security review, validation evidence, reviewers, rollback. No merge until appropriate reviews, CI gates, and Manager gate. Main protection requirement is open (no code merge W1).
6. Alembic: H-04 owns baseline and migration protocol; module work appends unique backend/alembic/versions/h-XX_*.py, never modifies older migrations. Coordinator checks revision graph/merge ordering. No overlap of two task branches editing shared configuration or shared frontend client.
7. Contract testing: actual YAML parsing plus OpenAPI 3.1 specification validator (version, command, output, GitHub blob SHA recorded); static reference-only checks are not equivalent to successful OpenAPI validation. Later OpenAPI conformance, negative 401/403/404/409/422 cases, IDOR, closed-period/race, F1/F2/F3 with actual HTTP+PostgreSQL evidence. Static contract review is not implementation PASS.

## No-overlap verification (against current authorized ledger)
- [x] H-02 paths docs/contracts/** and docs/architecture/** assigned to Coordinator only.
- [x] H-02 is W0; H-01 manager decision gate is evidenced; H-02 start_authorized=true; W0 entry_authorized=true.
- [x] UX H-17..H-20 design/** does not overlap H-02.
- [x] Developer H-03..H-25 code paths do not overlap H-02 (nor this PR).
- [x] QA qa/** and agent-specific report do not overlap H-02.
- [x] Official task ledger and waves are not edited in this PR; H-27 not begun.
- [x] rc.3 YAML parsing, independent vendor OpenAPI 3.1 schema validation function (@apidevtools/swagger-parser 11.0.0), and supplemental structural checks recorded with exact SHA/limits in docs/contracts/VALIDATION.md and validation-result.json.
- [ ] Full OAI dynamic-dialect schema-base / full vendor dereference pipeline if Manager requires this stricter additional gate (vendor internal workaround disclosed).
- [ ] Developer explicitly acknowledges revised OpenAPI version and SHA (pending future approved review).
- [ ] UI/UX explicitly acknowledges revised OpenAPI version and SHA (pending future approved review).
- [ ] Independent Manager freeze/review and W0 exit decision (pending).
- [ ] Main branch protection + required CI/PR gate before W1 code merges (pending).

## Open decisions / escalation
Manager PR #1 decision CHANGES_REQUIRED dated 2026-11-14: trial balance totals, initial user and invite onboarding, CSRF session binding and full 3.1 tooling validation. Those contract changes must be checked before either consumer acknowledges exact revised blob SHA. No unapproved agent activation; manager coordinates read-only consumer reviews.

Review is pending until both consumer acknowledgments and Manager gate are evidenced. OpenAPI design includes proposed details not specified by H-D01..09 (some route naming, request-size/paging limits and ownership role matrix). These are proposed interoperability choices, not separate authorization for W1. Document feedback in PR; do not declare W0 complete.

## Manager consumer-review decision APP-HESABYAR-H02-CONSUMER-FINDINGS-20261114-001
Developer and UI/UX rc.2 findings are CHANGES_REQUIRED, not accepted. Coordinator revises only H-02 docs and its own report; the approval gate for new rc.3 OpenAPI SHA resets consumer acknowledgments. The independent OpenAPI 3.1-compatible validator must use unchanged final YAML. No automatic activation of either consumer, PR merge, TASKS/WAVES edits or W1 task is authorized. Follow error and fixture contracts under docs/contracts/ERRORS.md and docs/contracts/TRIAL_BALANCE_FIXTURE.md. Formal freeze remains Manager-controlled.
