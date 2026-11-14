# Hesabyar V1.0 — Architecture Baseline
Task H-02 | Contract baseline: 1.0.0-rc.3 | 2026-11-14 | Owner: Coordinator | Status: PROPOSED FOR REVIEW

## Authorized decisions
Source of truth: .chatgpt-team/DECISIONS.md (H-D01..H-D09), TASKS.json, WAVES.json. W0/H-02 only; no production implementation or W1 authorization.

## Topology
Browser (React  + TypeScript + Vite + Tailwind, RTL/Jalali presentation)
  -> HTTPS same-origin /api/v1 (secure session cookie + CSRF protection)
  -> FastAPI modular monolith (routers -> application services -> domain -> SQLAlchemy repositories)
  -> PostgreSQL (transaction boundaries, scoped FK/unique/index, Alembic)
  -> append-only audit records for sensitive mutations.

Modules are packages, NOT distributed microservices. No direct browser-to-DB access or cross-module SQL writes. Cross-module orchestration occurs through application services and typed interfaces; a single DB transaction owns posting, numbering, period checks and audit emission. Public OpenAPI schemas are contract-first, not a claim of implemented endpoints.

## Module ownership & boundaries
| Module | Owns | Depends on / exposed behavior | H task |
|---|---|---|---|
| identity | user, password hash, sessions, CSRF, company membership, roles | principal and membership policy; no global superadmin | H-05 |
| companies | company lifecycle and company selection authorization | identity membership guard; company-scoped objects | H-06 |
| fiscal | years/periods, half-open Gregorian date ranges and closure | company; posting/close transactional lock protocol | H-07 |
| core.money | IRR integer rial validation, Decimal and numeric serialization | cross-cutting pure value object | H-08 |
| accounts | group/general/subsidiary/detail tree, postable leaves and scoped codes | company; fiscal independent catalog | H-09 |
| audit | actor/company/timestamp/action/redacted before-after append-only records | shared sink; no credential or other tenant disclosure | H-10 |
| journals | draft, balanced atomic posting, immutable posted data, reversal, sequence and idempotency | accounts, fiscal, identity, money, audit | H-11..H-14 |
| reports | posted-only source-of-truth ledger/daybook/trial balance queries | read-only journals/accounts/fiscal and access policy | H-15/H-16 |

**Identity bootstrap:** Initial company/owner is provisioned only by restricted audited operator action, not a publicly exposed registration/bootstrap endpoint. One-time hashed setup claim (<=15 min) activates pending owner with strong password, then normal login; no default password or global admin. A company-owner/admin can invite either existing or new email into *only that company* through a pending, hashed, expiring (<=48h), one-use invitation. Only the authenticated existing-email owner of an invitation (verified email) or new user with valid token plus strong password may accept it; acceptance creates membership atomically. Only existing company owner can invite owner role. Company-scoped owner membership may be granted to an activated brand-new principal only if original inviter is a currently authorized owner in that same company at issuance and acceptance. Admins cannot invite owner, no global privileges. No membership before acceptance and no client-specified tenancy/role override. Sessions and CSRF are bound and rotated; see docs/contracts/README.md and openapi.yaml.

Every tenant-owned row carries company_id; keys/references must enforce matching company boundaries. When an authenticated user has multiple memberships, selection scopes the active context but never grants permission by itself. API never trusts arbitrary company_id or header as proof of membership.

## Invariants and persistence
- Currency: IRR ONLY. Monetary amount is nonnegative whole rial serialized as JSON string matching ^(0|[1-9][0-9]*)$ (max 20 decimal digits, DB NUMERIC(20,0)); no JSON floats, exponents, fractional digits or implicit rounding. Transaction posting requires positive total.
- Canonical financial dates: ISO Gregorian YYYY-MM-DD; UI converts to/from Jalali; [start_date,end_date) period boundaries, no overlap per company. Event timestamps ISO 8601 UTC; accounting cutoff Asia/Tehran.
- Account levels: GROUP -> GENERAL -> SUBSIDIARY -> DETAIL; detail is bound to exactly one subsidiary, never floating. A subsidiary without detail children can be postable; a detail leaf can be postable; parent/disabled account cannot. Full code unique within company; used posted account cannot be deleted.
- Draft may be incomplete/unbalanced, but valid references must be company-scoped; no draft counts in financial reports. POSTED is immutable, never edited or deleted. `reversed` is a derived flag on original when a linked posted reversal exists, not an independent mutable voucher state.
- Posting requires >=2 valid lines, one-sided positive debit or credit per line, strictly equal positive sums, open containing period, sufficient role, and server-rechecked account state. All validations, sequence allocation, posted change and audit entry are atomic. Idempotency key is scoped by company/operation/principal (and request fingerprint) with deterministic conflict for differing payload; retries cannot double-post.
- Posted voucher numbers unique by (company, fiscal-year), monotonically allocated under concurrency and never re-used. Audit any skipped/voided allocation; prefer transactional assignment to minimize gaps, never fill gaps retroactively.
- Reversal is exactly one separately numbered posted voucher with inverted lines, linked to original, with no partial or duplicate reversal. Reversal must independently pass open-period, role and tenancy checks; original remains unchanged.
- Fiscal close/post race is serialized by transaction-level locks of the same fiscal period record; final decision obeys serialized order. Never check period openness only before entering transaction.
- Reads/exports/reports include only one authorized company and permitted fiscal/date scope. SQL uses scoped predicates AND database integrity constraints; IDOR requests are rejected without revealing other-company existence.
- Trial balance row/summary separation: `TrialBalanceRow` includes account_id and account_code; `TrialBalanceTotals` only six financial sums without account identity. At the requested hierarchy level, each posted leaf contributes to exactly one row; never sum overlapping ancestors/descendants. All-filtered-account totals (before page slicing) are independent of page/page_size. Opening before from_date, movements in [from_date,to_date), closing = opening plus net movement. Reports derive sums exclusively from POSTED lines including reversal lines. Opening before query start, period debit/credit, closing net and signed running balances must reconcile. F1: Dr movement=Cr movement=1,200,000, cash ending debit=800,000, expense debit=200,000, capital credit=1,000,000. F2 after reversal: movement 1,400,000 each side; closing debit/credit each 1,000,000. F3: deliberate cross-company IDs/codes must not leak.

## Internal interfaces and dependency direction
Authentication context -> company membership verification -> fiscal/account domain checks -> journal application orchestration -> transactionally persist -> audit. Reporting reads canonical posted journal stream, never private journal draft tables alone. Service functions receive explicit verified principal and company context; repositories never accept an unverified tenant selector. API adapters serialize Pydantic-compatible request/response DTOs; SQLAlchemy models never leak directly into JSON.

## Operational non-goals and risks
V1.0 excludes treasury, persons, statements/dashboard, CSV/Excel/PDF import/export, multicurrency and global superadmin. No public deployment or quantified SLA approved. Default no secrets; private staging only. PostgreSQL—not SQLite—is required for concurrency and migration evidence. W1 code merges require protected main, PR review and CI gates; currently protection is a known manager blocker.

## Consumer-review accounting and UI contracts (rc.3)
- **Complete leaf-level trial balance:** detail request is a mixed effective level of ALL postable leaves: DETAIL accounts and SUBSIDIARY accounts with zero DETAIL children. Every posted line maps exactly once. `TrialBalanceRow.account_level` distinguishes `detail` vs `subsidiary`; `account_name` supports direct display. Sum `TrialBalanceTotals` over all filtered eligible rows before pagination. At general or subsidiary selection, each posted leaf rolls up to one ancestor, never both parent and leaf in totals. The invariant is valid on each page because `totals` is global for the filtered set, not page-local. See [mixed fixture](../contracts/TRIAL_BALANCE_FIXTURE.md): standalone subsidiary A debit 100, detail B credit 100, returned on two pages with same totals 100/100.
- **Structured voucher error semantics:** Draft warnings have stable typed code/message plus optional JSON Pointer field and zero-based line_index; allow incomplete saved drafts, reject unsafe company mismatches, return positive accumulated valid debit/credit totals for every draft. Posting still enforces strict balance and closed-period rules. Report journal movement identifies each line by UUID `line_id`, stable line_index, persisted description and account_name/account_code/account_level; sorting includes date/voucher/line index/id. [Errors](../contracts/ERRORS.md).
- **Jalali date range:** DB and API carry Gregorian start inclusive/end exclusive, timestamps UTC, accounting cutoff Asia/Tehran. UI shows inclusive last Jalali day by subtracting one day from exclusive Gregorian end and converting date-only. To submit inclusive Jalali last day, convert date to Gregorian and add one day.
- **CSRF UX:** First CSRF_INVALID freezes mutation; GET token at most once with same browser session; no unsafe request automatically replayed. User reviews and explicitly resubmits; if refresh fails, display security retry panel, 401 requires re-login and company/period recheck. Never store token in localStorage/URL.
