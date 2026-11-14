# ui-ux / REPORT

## 2026-11-14 — H-02 consumer contract review (read-only assessment)

- Scope authorization: `APP-HESABYAR-W0-CONTRACT-REVIEW-20261114-001`; PR [#1](https://github.com/Ana0251/ChatGPT-Team-Test/pull/1).
- Exact baseline evaluated: OpenAPI `1.0.0-rc.2`; `docs/contracts/openapi.yaml` Git blob SHA `c7d45ebfb715aea6960f130648ebfde148c93e54` (verified by direct GitHub fetch); PR HEAD before this reporting commit `d0067c98c6c5fc2f883dbf0baf715ad797818119`.
- Materials read: UI/UX prompt and role, manager DECISIONS, TASKS/WAVES, UI/UX inbox/memory, OpenAPI, contracts README/VALIDATION and architecture README/OWNERSHIP_AND_REVIEW, manager PR review.
- Disposition: **CHANGES_REQUIRED / UI/UX DOES NOT ACKNOWLEDGE CONTRACT FREEZE**. This is a static consumer-design review, not implementation testing, security validation, OpenAPI full conformance, QA PASS or W0 approval.

### Usable baseline
- Architecture supports Persian RTL/Jalali front end; dates cross API as ISO Gregorian `date`, UTC event timestamps and Tehran accounting cutoff. UI should convert dates explicitly, with exclusive reporting end-date semantics.
- `/auth/csrf`, `/auth/login`, `/auth/me`, company membership and fiscal endpoints provide baseline login, company/year selection, invite and activation flows.
- Account tree and `postable` flag support the scoped four-level code picker; drafts may be incomplete/unbalanced with warnings; posting, reversal, immutable posted state, idempotency key and period close support distinct interactions.
- Reporting endpoints cover daybook, account ledger and trial balance. Financial values use decimal strings (IRR whole-rial), allowing exact display with string/integer-safe formatting and no JS Number coercion; signed ledger balances use `SignedRial`.
- `ErrorEnvelope` provides `code/message/request_id/details[]`; session CSRF uses pre-session binding and refresh-once without unsafe automatic mutation replay.

### Blocking consumer findings
1. **P0: trial balance at `level=detail` omits or ambiguously maps postable subsidiary leaves.** Architecture permits posting to a subsidiary account without detail children, but `TrialBalance` promises homogeneous selected-level rows and exactly one selected-level ancestor for every posted leaf. A subsidiary leaf has no detail ancestor. Define explicit behavior (mixed postable-leaf rows with `account_level`, or partial detail-only scope and reconciled scope-specific totals), plus fixture and no-hidden-movements guarantee; do not show a false balanced total.
2. **P0: company-owner invite cannot be consistently presented.** `POST /companies/{companyId}/members` permits existing company owner to invite a new email as `owner`, while `POST /auth/invitations/activate` says `Never creates owner`. Decide whether a new principal may get company-scoped owner (not global admin), or prohibit owner invitations to new emails with specified API validation error.
3. **P1: error UX contract underspecified.** Envelope is useful, but stable documented error-code taxonomy per operation, machine-readable `details[].field` path / `reason` values and localization/message safety are not enumerated, particularly `PERIOD_CLOSED`, `UNBALANCED`, `ACCOUNT_NOT_POSTABLE`, invitation expiry and CSRF errors. UI cannot reliably render inline Persian field feedback and recovery based solely on prose and arbitrary strings.
4. **P1: CSRF recovery journey.** One refresh and no blind replay is good; specify user-visible recovery after refresh fails, expired authenticated session versus invalid pre-session, and whether safe retry requires explicit resubmission after a fresh token. Do not leak token in UI or URLs.
5. **P1: draft warning payload.** `Journal.warnings` is `string[]` without stable codes or line indices/field paths. For RTL multi-line voucher editing, localizing warnings and focusing the erroneous row is ambiguous. Define structured optional warning entries or stable localization codes.
6. **P1: OpenAPI validation remains qualified.** Existing evidence explicitly says unmodified OAI OpenAPI 3.1 dialect validation did not pass (329 errors) and documented CLI was not executed. Independent clean validation of unchanged source is required before freeze. UI review cannot serve as spec validation.

### Secondary clarifications (nonblocking after P0/P1 resolution)
- Fiscal `FiscalPeriod` extends `FiscalYear` and requires `company_id`; clarify whether period display expects `name`, `year_id` and half-open bounds. Ensure UI labels inclusive end as previous Jalali day, not exclusive boundary day.
- Report `Movement` lacks line ID, line description and account name/code, limiting descriptive daybook display and stable row keys when multiple lines share voucher/account/date. Document stable sorting/tie-breaker and row identity or enrich representation.
- `TrialBalanceRow` lacks account name/level, requiring catalog join in UI; add display-safe name and actual effective level if mixed rows approved.
- `Journal.total_debit/total_credit` are optional while `warnings` is required; document whether totals are always returned (including incomplete drafts) for a consistent balance indicator.

### Restrictions and next gate
No product or design files were edited; no H-17/H-03, QA, TASKS/WAVES, W1 or merge work was started. Coordinator should resolve P0/P1 findings and provide a new contract version/SHA if the OpenAPI changes. UI/UX acknowledgment must be repeated on that **final exact blob**, after manager authorization and successful validation; current SHA is **not approved**.
