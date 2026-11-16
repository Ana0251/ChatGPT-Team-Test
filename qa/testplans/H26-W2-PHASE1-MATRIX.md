# H-26 | W2 Phase 1 — Independent QA risk-based test matrix (H-03 to H-08)

**State:** PLAN_READY_FOR_COORDINATOR_REVIEW; **QA_RUNTIME_NOT_RUN**. **Not** H-26 COMPLETED, W2 exit, release acceptance, or an executed QA PASS.

## Authority / provenance

- Repository `Ana0251/ChatGPT-Team-Test`; Framework **1.3.0**; Manager decision `APP-HESABYAR-W2-PHASE1-ENTRY-20261116-001`, [handoff PR #70 comment 6910826842](https://github.com/Ana0251/ChatGPT-Team-Test/pull/70#issuecomment-6910826842).
- **Baseline proposed for independent retest**: `main@d18028d2409561bb3b993aaaef8d8f4f4bbceb53` (verify immediately before executing). Approved [OpenAPI rc.4](../../docs/contracts/openapi.yaml), Git blob `f57de031224e21f09253642c210a778a60683711`. A future head change requires recorded new SHA and impact review.
- H-26 owner QA, `review_policy=coordinator_required`, `status=AUTHORIZED_NOT_STARTED`, `start_authorized=true`, `validation_status=NOT_TESTED`. W2 `AUTHORIZED_NOT_STARTED`; W3–W5 not authorized. This is **first incremental QA handoff**, not completion of multiwave H-26.
- Previously delivered W1 H-03–H-08 local modules: health, SQLite/Alembic, identity/auth, companies, fiscal, pure Rial/Decimal helpers. H-08 owner H-08 158 PASS and full Backend 229 PASS included 158, **not additive**. Historical W1 QA evidence is source-review `PASS LIMITED` and owner-run Pytest, **not QA-executed**.
- Source files checked from current main: `backend/tests/test_health.py`; `tests/db/test_migrations.py`; `tests/identity/test_auth_flows.py`; `tests/companies/test_companies.py`; `tests/fiscal/test_fiscal.py`; `tests/core/test_money.py`, `backend/app/modules/identity/{router,store}.py`, contract rc.4. All scenarios below are **planned**, and each execution result is **NOT_RUN** until logged.

## Severity and evidence semantics

**P0** = integrity/financial loss or severe security failure; **P1** = tenant auth/privilege/transaction break or significant availability; **P2** = relevant input/compatibility/error handling; **P3** = secondary UX/logging/warnings. Priority is *risk if defect discovered*, **not** an assertion that a defect exists. Every `PLAN_ONLY / NOT_RUN` row has no actual observed behavior or Exit Code. Evidence labels: `SOURCE_REVIEW_PASS_LIMITED`, `OWNER_RUNTIME_PASS` (historical only), `QA_RUNTIME_PASS/FAIL` only for new QA executions, `QA_RUNTIME_NOT_RUN`, `DEFERRED_NOT_TESTED`.

### Executable and manual negative-case matrix

| ID | Source | Risk | Preconditions and action/input | Expected observable result / exit outcome | Existing test mapping | QA result |
|---|---|---|---|---|---|---|
| H26-F01 | H-03 | P2 | Factory app and GET `/health` | 200 JSON `{"status":"ok"}`; no DB startup/secret leak | `tests/test_health.py::test_health_endpoint_returns_ok` | NOT_RUN |
| H26-F02 | H-03 | P2 | Unknown route / configurable app name | 404 for unknown; configured title used | `tests/test_health.py` remaining two cases | NOT_RUN |
| H26-D01 | H-04 | P0 | Disposable SQLite; upgrade H04 then downgrade/re-upgrade | schema deterministic, migration reproducible, no leftover tables | `tests/db/test_migrations.py::test_upgrade_downgrade_upgrade_uses_isolated_database` | NOT_RUN |
| H26-D02 | H-04 | P0 | New SQLite connection incl independently opened connections | `PRAGMA foreign_keys=1`; invalid FK insert rejected | `tests/db/` and `tests/identity/test_identity_migration.py` | NOT_RUN |
| H26-D03 | H-04–07 | P1 | Upgrade current head on disposable DB, H05/H07 reverse tests | H05→H07→H05→H07 preserves H05 baseline, no unsafe existing-data loss; foreign key checks | `tests/fiscal/test_fiscal.py::test_migration_is_additive_reversible_and_reappliable`; `tests/identity/test_identity_migration.py` | NOT_RUN |
| H26-I01 | H-05 | P0 | Anonymous/expired-cookie GET `/auth/me` and member resources; bad credentials | 401 neutral; no session/secret leakage or privilege escalation | `tests/identity/test_auth_flows.py::test_login_csrf_origin_and_401_422`; `test_logout_revocation_and_expiry` | NOT_RUN |
| H26-I02 | H-05 | P0 | Login/logout; reuse invalidated or expired auth session | Secure HttpOnly SameSite cookies, rotation and revoked/expired sessions rejected | `test_password_strength_no_plaintext_and_session_rotation`; `test_logout_revocation_and_expiry` | NOT_RUN |
| H26-I03 | H-05 | P0 | Every unsafe auth/invitation endpoint with missing/wrong CSRF, missing/foreign Origin | 403; no mutation or leaked token; valid same-origin HTTPS CSRF works | `test_pre_session_requires_origin_and_token`; `test_origin_missing_with_valid_header_is_denied` | NOT_RUN |
| H26-I04 | H-05 | P0 | Bootstrap owner token twice / expired / wrong operator secret | One-use fail closed; no duplicate owner or plaintext credentials | `test_initial_owner_is_restricted_and_single_use`; `test_bad_operator_key_and_expired_bootstrap` | NOT_RUN |
| H26-I05 | H-05 | P1 | Viewer invites, admin attempts owner invite, revoked inviter, wrong recipient accepts | 403 or safe deny; membership only current authorized scope, no role escalation | `test_viewer_cannot_invite_or_read_members`; `test_admin_can_invite_viewer_but_not_owner`; `test_invitation_issuer_role_rechecked_and_token_hash_only` | NOT_RUN |
| H26-I06 | H-05 | P1 | Invitation issuer 21st event within 24h and company 51st across issuers | 409 `INVITE_RATE_LIMITED` ErrorEnvelope rc.4; no extra token/email/row/audit; other tenants not impacted | `test_invitation_rate_limit_matches_approved_openapi[issuer]`; `[company]`; existing quota tests | NOT_RUN |
| H26-I07 | H-05 | P1 | Duplicate invitation; expired/reused/recipient-mismatch token | No duplicate membership; no exposure of other tenants or tokens | `test_existing_user_accepts_invite_once_and_email_checked`; `test_invite_expiry_issuer_revocation_and_duplicate_membership` | NOT_RUN |
| H26-C01 | H-06 | P0 | Owner lists companies; unrelated member queries foreign `companyId` | Only live memberships listed, foreign/missing both neutral 404 without name leak | `tests/companies/test_companies.py::test_nonmember_and_missing_company_have_indistinguishable_404` | NOT_RUN |
| H26-C02 | H-06 | P1 | Authenticated POST `/companies` with injected `owner_id` or `role` | 422; created owner always signed-in session principal, no client authority | `test_company_create_only_authenticated_user_even_with_untrusted_payload` | NOT_RUN |
| H26-C03 | H-06 | P1 | Force owner-membership INSERT failure after company INSERT | Atomic rollback: no orphan company or membership | `test_company_creation_rolls_back_if_owner_membership_insert_fails` | NOT_RUN |
| H26-C04 | H-06 | P1 | Revoke member; then list/detail and attempt cross-company switch | Membership effect immediately visible: missing company in list, 404 detail | `test_nonmember_and_missing_company_have_indistinguishable_404`; `test_unaccepted_member_cannot_select_other_company` | NOT_RUN |
| H26-C05 | H-06 | P2 | POST name empty/blank/201 chars, 200 chars, bad Origin/CSRF/expired session | 422 invalid; 201 200-char boundary, 403 invalid origin/csrf, 401 expired | `test_company_name_validation_422`; `test_company_name_max_length_boundary`; `test_company_create_csrf_origin_and_expired_session` | NOT_RUN |
| H26-Y01 | H-07 | P0 | Same-company fiscal years overlapping vs touching end/start, reverse/invalid dates | Overlap 409 `PERIOD_OVERLAP`; adjacent 201; invalid date 422 | `tests/fiscal/test_fiscal.py::test_year_adjacency_overlap_and_date_validation` | NOT_RUN |
| H26-Y02 | H-07 | P0 | Periods overlapping, touching boundaries, outside year / zero-length | Reject 409/422 with standard envelope; adjacency permitted, contained period `open` | `test_period_adjacency_overlap_containment_and_close` | NOT_RUN |
| H26-Y03 | H-07 | P0 | Mismatched company/year/period IDs, viewer tries create/close, revoked membership | Neutral 404 across tenancy/parent, 403 role denial; no write | `test_no_cross_tenant_or_cross_parent_idor`; `test_mutation_csrf_origin_expiry_and_roles` | NOT_RUN |
| H26-Y04 | H-07 | P0 | Owner/admin closes open period then repeats; inject audit INSERT failure | First 200+UTC audit+status closed, repeat 409 `PERIOD_CLOSED`; failure rollback leaves open/no audit | `test_period_adjacency_overlap_containment_and_close`; `test_close_rolls_back_on_audit_failure` | NOT_RUN |
| H26-Y05 | H-07 | P1 | Three fiscal POST endpoints with absent/wrong Origin/CSRF; expired session | 403 for CSRF/Origin, 401 for session; no period mutation | `test_mutation_csrf_origin_expiry_and_roles` | NOT_RUN |
| H26-R01 | H-08 | P0 | `parse_rial` 0, 1 and max 99999999999999999999; serialize and JSON roundtrip | Only ASCII decimal string, exact Decimal and exact returned canonical text | `tests/core/test_money.py::test_rial_canonical_values_roundtrip_and_json_ascii` | NOT_RUN |
| H26-R02 | H-08 | P0 | 21-digit 100000000000000000000; MAX+1, high two-operand sum and aggregate overflow | `RialValueError` on parse, addition or sum; never truncate/saturate/round | `test_exact_sum_detects_twenty_digit_overflow`; `test_multi_item_aggregation_and_intermediate_overflow` | NOT_RUN |
| H26-R03 | H-08 | P0 | Float/int/bool/null, negative/-0, Unicode digits, NaN/Infinity, fraction/exponent/leading zeros | Reject; no implicit JSON number coercion or invisible rounding | `test_actual_json_numeric_and_non_string_values_rejected`; `test_reject_invalid_noncanonical_wire_values` | NOT_RUN |
| H26-R04 | H-08 | P0 | Caller Decimal context precision 2 + rounding traps; exact 20-digit addition | Exact output independent of ambient context; no false PASS due to rounding | `test_arithmetic_never_implicitly_rounds_under_low_caller_precision` | NOT_RUN |
| H26-R05 | H-08 | P0 | Negative SignedRial report input passed to ordinary Rial journal helpers; -0 | Report-only helpers may accept -1; ordinary Rial rejects negatives; -0 rejected globally | `test_signed_report_roundtrip_separate_from_journal`; `test_signed_report_rejects_noncanonical_wire` | NOT_RUN |
| H26-R06 | H-08 | P1 | Actual approved OpenAPI YAML and Rial/SignedRial regex | rc.4 schema string types & canonical ASCII regex match helpers | `test_approved_openapi_rc4_rial_and_signed_patterns` | NOT_RUN |
| H26-X01 | H-03–08 | P0 | Run full `backend/tests` at exact checked-out main SHA | No failures; record all PASS/FAIL/SKIP/WARN and real Exit Code; compare prior owner suite as historical only | `py -3.14 -m pytest -v tests` | NOT_RUN |
| H26-X02 | H-05–07 | P1 | Actual 409/404/422 JSON error envelope and `request_id`, no-store under TestClient | Response schema and redaction per rc.4; forbidden resource not disclosed | H05 quota OpenAPI tests + H06/H07 HTTP negative tests; add stricter schema cases only after authorization | NOT_RUN |

**Coverage interpretation:** Existing Pytest function names are exact references to checked-in sources; a row can map to several parametrized cases. This matrix is **not** a claim that 29 standalone executable new tests were authored or run; it is a traceable QA execution plan and mapping to existing real tests.

## Explicit deferred gates, outside currently testable W1 local scope

| ID | Priority | Dependency and expected future proof | Status |
|---|---|---|---|
| H26-Z01 | P0 | PostgreSQL provisioned, `NUMERIC(20,0)` driver roundtrip, FK/check and transaction/row-lock races | DEFERRED_NOT_TESTED |
| H26-Z02 | P0 | Implemented journal Posting/Reversal; balanced posting, immutable posted documents, duplicate request safety | DEFERRED_NOT_TESTED |
| H26-Z03 | P0 | Real Posting + period close concurrently: period lock, no late postings, atomic rollback/audit | DEFERRED_NOT_TESTED |
| H26-Z04 | P0 | Implemented F1/F2/F3 accounting flows with independent reconciled fixtures, reports from POSTED only | DEFERRED_NOT_TESTED |
| H26-Z05 | P1 | Authorized realistic browser/proxy HTTPS, SameSite cookies, CSRF/Origin and RTL accessibility | DEFERRED_NOT_TESTED |
| H26-Z06 | P0 | Actual backup → delete/recreate isolated environment → restore/reconcile records | DEFERRED_NOT_TESTED |
| H26-Z07 | P1 | Authorized adversarial multi-tenant penetration, network proxies, multiworker load and leak analysis | DEFERRED_NOT_TESTED |
| H26-Z08 | P1 | Actual Iranian Jalali UI and Asia/Tehran fiscal cutoff with timezone-boundary tests | DEFERRED_NOT_TESTED |

## Reproduction protocol and machine-readable evidence

Follow [phase-1-runbook](W2-PHASE1-RUNBOOK.md) and [initial evidence status](../evidence/H26-W2-PHASE1-STATUS.md). Pin exact main commit, use disposable SQLite database and only authorized local environment. For every case capture actor, UTC timestamp, OS/Python/Pytest/SQLite versions, `git rev-parse HEAD`, clean tracked status, command, sanitized input, expected/observed output, exit code, PASS/FAIL/SKIP, warnings, stdout/stderr artifact, and issue/PR URL for defects. Any P0/P1 failure: stop certification, document reproduction with least data disclosure and seek Manager decision. Coordinator must review H-26 owner-produced evidence; QA **must not self-approve**.

**No execution performed in this stage: `QA_RUNTIME_NOT_RUN`.** The current GitHub connector gives repository access but no authenticated, exact-commit Windows QA runtime. No user-provided local checkout/test-system access has been granted here. Proposed run steps do not create or claim results.
