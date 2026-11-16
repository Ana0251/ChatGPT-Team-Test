# H-26 W2 Phase-1 — Independent QA runbook (PROPOSED, NOT EXECUTED)

**Execution status:** `QA_RUNTIME_NOT_RUN` — commands below are reproducible instructions, **not an execution transcript**. They are for an **authorized QA runner** with a separate disposable checkout and test database. Do not run in production or replace evidence from the owner with QA labels. Base commit at planning time: `d18028d2409561bb3b993aaaef8d8f4f4bbceb53`; contract OpenAPI rc.4 blob `f57de031224e21f09253642c210a778a60683711`. Test the exact commit provided or record any approved later SHA and reconsider coverage.

## 1. Preconditions and safeguards

- Obtain Manager approval for the exact QA runner and sandbox; ensure real Python 3.14.x and installed `backend[ test ]` extras or equivalent project test environment. **No authorized execution environment is available within this QA conversation.**
- Use an isolated test checkout underneath an existing scratch root, e.g. `D:\\Codex\\Temp\\H26-independent-qa` only when that location is available and authorized; **never create a new directory directly under D:\\**. Never run against production DB, SMTP, secrets or real customers.
- Prefer a separately provisioned disposable virtual environment with `python -m pip install -e ".[test]"` inside `backend` **only if installing dependencies is authorized**. Dependencies are declared in `backend/pyproject.toml`. Keep `HESABYAR_DATABASE_URL` unset or targeted to a fresh disposable location; fixture tests use `tmp_path` and override it. All test principals/emails use synthetic `example.test` data.
- Store complete logs under the QA evidence location or protected authorized scratch path. Redact bearer/session cookies, CSRF secrets, tokens, operator keys, personal information and untrusted URLs prior to attaching evidence.
- Do not equate a successful process exit with full coverage; note warnings, pytest deselection, skipped tests and any pre-existing failed checks. Do not execute network load, external pentests or irreversible tests without separate authorization.

## 2. Baseline / provenance commands (PowerShell on an authorized test checkout)

```powershell
$ExpectedSha = 'd18028d2409561bb3b993aaaef8d8f4f4bbceb53'
$Repo = 'D:\Codex\Temp\H26-independent-qa' # Replace only with actual separately authorized checkout
Set-Location $Repo
git rev-parse HEAD
git status --porcelain
# Confirm git HEAD exactly equals $ExpectedSha, and no modified tracked source/test files.
# Record all untracked files and distinguish generated artifacts from unexpected data.
py -3.14 --version
py -3.14 -c "import sqlite3; print(sqlite3.sqlite_version)"
Set-Location (Join-Path $Repo 'backend')
py -3.14 -m pytest --version
py -3.14 -m pip freeze
```

**HOLD if:** HEAD does not match the approved SHA, runtime/dependencies are missing, tracked modifications are present, unapproved DB endpoints are configured or test sandbox scope is unclear. Do not call tests PASS after a hold. Capture UTC timestamp and operator identity at runtime.

## 3. Actual execution commands (provided, not run)

For each line record the printed Pytest summary, `$LASTEXITCODE`, warnings and elapsed time separately. The Python executable and worktree SHA must be the same across the suite, or the divergence must be stated.

```powershell
# QA-EXEC-H03: app health / factory
py -3.14 -m pytest -v tests/test_health.py
$ExitH03 = $LASTEXITCODE

# QA-EXEC-H04: SQLite/Alembic and DB isolation
py -3.14 -m pytest -v tests/db
$ExitH04 = $LASTEXITCODE

# QA-EXEC-H05: session, CSRF/Origin, invitation role/quota and schema
py -3.14 -m pytest -v tests/identity
$ExitH05 = $LASTEXITCODE

# QA-EXEC-H06: company tenant/role/atomic create
py -3.14 -m pytest -v tests/companies
$ExitH06 = $LASTEXITCODE

# QA-EXEC-H07: fiscal intervals, period close, migration and audit
py -3.14 -m pytest -v tests/fiscal
$ExitH07 = $LASTEXITCODE

# QA-EXEC-H08: canonical Rial, Decimal precision, signed reporting
py -3.14 -m pytest -v tests/core/test_money.py
$ExitH08 = $LASTEXITCODE

# QA-EXEC-ALL: full regression including all previous modules
py -3.14 -m pytest -v tests
$ExitAll = $LASTEXITCODE

[pscustomobject]@{
 H03=$ExitH03; H04=$ExitH04; H05=$ExitH05;
 H06=$ExitH06; H07=$ExitH07; H08=$ExitH08; Full=$ExitAll
}
```

**Expected outcome** from previously reported OWNER-run baseline is no failing tests for the delivered W1 scope (last owner full run 229 PASS, 54 warnings), but **do not pre-fill real QA results**. Counts may change if approved HEAD or dependency environment changes. Full suite already includes module suites; **never add module counts to full suite to claim distinct tests**. When evidence is generated, attach source-specific full Pytest output and a manifest with SHA, actor, local UTC timestamps and all seven exit codes.

## 4. Focused negative/security/boundary retest commands

Run these existing individual functions for explicit auditable negative-case logs in addition to broad suite outputs. Some parametrized functions execute multiple cases.

```powershell
# Multi-tenant and role checks — H05/H06
py -3.14 -m pytest -v tests/identity/test_auth_flows.py::test_cross_tenant_ids_are_invisible tests/identity/test_auth_flows.py::test_invitation_rate_limit_matches_approved_openapi
$ExitTenantAndQuota = $LASTEXITCODE
py -3.14 -m pytest -v tests/companies/test_companies.py::test_nonmember_and_missing_company_have_indistinguishable_404 tests/companies/test_companies.py::test_company_create_only_authenticated_user_even_with_untrusted_payload tests/companies/test_companies.py::test_company_creation_rolls_back_if_owner_membership_insert_fails
$ExitCompanySecurity = $LASTEXITCODE

# Fiscal boundary / roles / rollback — H07
py -3.14 -m pytest -v tests/fiscal/test_fiscal.py::test_year_adjacency_overlap_and_date_validation tests/fiscal/test_fiscal.py::test_period_adjacency_overlap_containment_and_close tests/fiscal/test_fiscal.py::test_no_cross_tenant_or_cross_parent_idor tests/fiscal/test_fiscal.py::test_close_rolls_back_on_audit_failure
$ExitFiscalNegative = $LASTEXITCODE

# IRR canonical, overflow and caller-context rounding — H08
py -3.14 -m pytest -v tests/core/test_money.py::test_actual_json_numeric_and_non_string_values_rejected tests/core/test_money.py::test_exact_sum_detects_twenty_digit_overflow tests/core/test_money.py::test_arithmetic_never_implicitly_rounds_under_low_caller_precision tests/core/test_money.py::test_signed_report_roundtrip_separate_from_journal
$ExitMoneyNegative = $LASTEXITCODE
```

Focus on **observed negative tests** returning the correct denial/error, not merely a 200 elsewhere. For every failure, minimize/redact repro and document PR/commit, fixture precondition, input, expected vs observed status/code/body, DB side effect and impact. **No specific new defect was observed in this planning stage.**

## 5. Real execution evidence template (fill only after running)

```text
Run ID: H26-W2-P1-<actual UTC timestamp>-<case ID>
Executor: <real QA operator or runner>
Date/time (UTC): <actual>
Repo/branch/commit: <git rev-parse HEAD actual>
Git tracked status: <actual>
Contract blob: f57de031224e21f09253642c210a778a60683711 (verify on tested tree)
Environment: OS, Python, pytest, sqlite3, SQLAlchemy, Alembic, test dependency freeze
Command: <exact command>
Fixture / input: <synthetic data and preparatory commands>
Expected result: <per plan>
Observed stdout/stderr (redacted): <link + summary>
Tests: <PASS x / FAIL y / SKIP z, warnings count>
Exit code: <actual $LASTEXITCODE>
Status: QA_RUNTIME_PASS | QA_RUNTIME_FAIL | QA_RUNTIME_NOT_RUN
Defect/PR link: <if any>
Limitations: <actual>
```

Store evidence in `qa/evidence/**` or attach a GitHub link under the same path. If QA cannot independently access an authorized runner, leave all real fields **NOT_RUN** and notify Manager/Coordinator.

## 6. Gating and review

- **H-26 stays open across W2–W5.** Current phase-1 deliverable is only matrix, executable commands and a truthful evidence gap.
- Coordinator is **mandatory independent reviewer** of H-26 QA-owned artifacts before Manager's decision. QA cannot validate/merge its own work.
- PostgreSQL/NUMERIC(20,0), actual Posting/Reversal, close-vs-post competition, F1/F2/F3, real browser HTTPS/CSRF, penetration, restore, production accounting and release are `DEFERRED_NOT_TESTED` pending implementation, environment and Manager authorization.
