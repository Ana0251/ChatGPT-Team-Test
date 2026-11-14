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

## 2026-11-14 — H-02 rc.3 re-review: UI/UX CONSUMER APPROVED

- Manager read-only authorization: `APP-HESABYAR-W0-RC3-REVIEW-20261114-001`; PR #1.
- **Exact reviewed contract:** `docs/contracts/openapi.yaml`, **`1.0.0-rc.3`**, GitHub **blob SHA `98d34e7bd7b4551c0f429ea5e388781060ceaf63`**, independently matched via direct GitHub file fetch. PR branch HEAD at review: `586f7b70e6280264e9c423b540a2a2a4306b8cc4`.
- Read directly: UI/UX prompt/role, Manager DECISIONS, task/wave ledgers, UI/UX inbox/memory, OpenAPI source and contract README, ERRORS.md, TRIAL_BALANCE_FIXTURE.md, validation evidence, architecture/ownership docs and prior own report.
- **Verdict: APPROVED as UI/UX contract consumer for this exact rc.3 SHA.** All previous blocking UI-contract objections have been addressed in normative fields and linked documentation; no remaining UI/UX contract blocker found.

### Prior findings disposition
1. **P0 trial balance — RESOLVED.** `level=detail` includes DETAIL leaves and directly postable SUBSIDIARY leaves. `TrialBalanceRow.account_name/account_level` required; `TrialBalanceTotals` includes all matching rows before pagination without double-counting. Fixture shows 100 debit at standalone subsidiary and 100 credit at detail, split across pages but totals 100/100 on both.
2. **P0 new-email company owner invitation — RESOLVED.** Company owner (not admin) may invite new email as owner of only the selected company. Token/email/company/role and inviter authority verified at issuance/acceptance; no global superadmin.
3. **P1 error localization — RESOLVED.** `ErrorCode`, `FieldIssue`, JSON Pointer `field`, zero-based `line_index`, stable `reason` and `ERRORS.md` operation mapping enable localized Persian fields/errors without parsing raw server messages.
4. **P1 voucher warnings — RESOLVED.** `JournalWarning[]` typed code/field/line_index, and required `Journal.total_debit/total_credit` on draft and posted responses; incomplete drafts can be retained with actionable warnings, posting checks remain strict.
5. **P1 CSRF recovery — RESOLVED.** Refresh token once, freeze original mutation, no automatic replay, human review and explicit resubmit; session expiry requires reauthentication/company+period recheck, error panel on repeated failure; token never persisted in browser storage or URL.
6. **Ledger/daybook — RESOLVED.** Movement requires `line_id`, `line_index`, description, account code/name/level with stable ordering, supporting RTL tables and row keys.
7. **Jalali/IRR — RESOLVED.** API date-only Gregorian, UI Jalali conversion, previous Gregorian day for display of exclusive end boundary, Tehran cutoff; amounts remain exact decimal strings in whole IRR (frontend must not coerce to floating-point Number).
8. **OpenAPI validation — QUALIFIED, non-UX gate.** Independent `@apidevtools/swagger-parser 11.0.0` vendor schema validation function is recorded PASS on unchanged YAML; full `SwaggerParser.validate()`, Node CLI, runtime/DB and independent QA are explicitly NOT_RUN. Validation/CI/freeze remains Coordinator/Manager gate, not implied by consumer approval.

### Scope and restrictions
Only the UI/UX consumer contract is approved, not technical conformance, security acceptance, runtime implementation, PR merge, H-02 completion, W0 exit or W1 start. New contract blob requires fresh UI/UX acknowledgment. No H-17/H-18/H-19/H-20 design tasks, code, QA, ledger changes or other-agent activations performed. This report update and PR comment are the only authorized writes.

## 2026-11-14 — H-18 identity/company-period UX specification handoff

- **Framework:** `1.3.0` (verified `.chatgpt-team/FRAMEWORK_VERSION.json`); read `.chatgpt-team/prompts/ui-ux.md`, role rules, TASKS/WAVES, DECISIONS, H-17 design files, relevant frozen H-02 OpenAPI and error contract directly from GitHub.
- **Authorization:** Manager decision `APP-HESABYAR-W1-H04-H18-ENTRY-20261114-001`; H-18 `AUTHORIZED_NOT_STARTED`, `start_authorized=true`; W1 `entry_authorized=true`; dependencies H-02 and H-17 `COMPLETED`. Ledger states not changed by UI/UX.
- **Base main commit:** `a972e31e0f108b97097e26822ceecb14b6e0d1a9`. **Contract:** OpenAPI `1.0.0-rc.3`, exact blob `98d34e7bd7b4551c0f429ea5e388781060ceaf63`; verified unchanged in H-18 branch.
- **Branch:** `feature/h-18-identity-company-period-ux`. **PR:** [#17](https://github.com/Ana0251/ChatGPT-Team-Test/pull/17). **Feature-design commit at PR creation:** `f7761e0ed73171b9577b8a54dbc9166dd7da5186`.
- **Files:** `design/specs/identity/AUTH_AND_INVITATIONS.md`, `design/specs/identity/SESSION_STATES.md`, `design/specs/company-period/COMPANY_FISCAL_SELECTION.md`, `design/specs/company-period/STATE_MATRIX_AND_REVIEW.md`. A checked GitHub commit comparison showed these four design-only additions and no other modifications before this role-report append.
- **Coverage:** login/logout/session expiry/CSRF explicit recovery, initial owner and two invitation activation modes, scoped company/role switching, fiscal-year/period selection with Jalali and exclusive-end, Loading/Empty/Error/Permission Denied, RTL/two themes/360px, state matrices and 19-point review checklist.
- **Evidence:** File paths and contract SHA verified from GitHub; document criteria **SPECIFIED**, real rendered UI, mobile/keyboard/screen-reader, API, authorization and security **NOT_TESTED**. This is not QA PASS.
- **Review policy:** H-18 lacks explicit `review_policy`, thus v1.3.0 legacy `Coordinator → QA` applies. Await independent Coordinator integration assessment first, then QA; final merge and task closure require Manager decision. No direct QA claim or independent review invented.
- **Scope:** no frontend/backend/OpenAPI changes, H-19 or other tasks started, PR merged, or task/wave status rewritten.
