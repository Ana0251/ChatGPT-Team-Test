# developer / REPORT

## 2026-11-14 — H-02 read-only API contract consumer review

**Decision:** CHANGES_REQUIRED — NOT ACKNOWLEDGED FOR FREEZE.
**Authorized by:** APP-HESABYAR-W0-CONTRACT-REVIEW-20261114-001.
**PR:** https://github.com/Ana0251/ChatGPT-Team-Test/pull/1
**Reviewed version:** `1.0.0-rc.2`
**Reviewed OpenAPI blob SHA:** `c7d45ebfb715aea6960f130648ebfde148c93e54`
**PR head before reporting:** `d0067c98c6c5fc2f883dbf0baf715ad797818119`

### Findings
1. **BLOCKER — detail trial balance completeness.** `docs/architecture/README.md` explicitly allows posting to a postable SUBSIDIARY without DETAIL children; `docs/contracts/openapi.yaml` `TrialBalance` specifies exactly-one ancestor at requested `level=detail`. Such a subsidiary has no detail ancestor. A direct-posted movement may disappear from detail rows and produce misleading `totals`/Dr=Cr claims. Define `detail` to include all postable leaves with actual `account_level` per row (or clearly scope an intentionally partial report, without implying global balance); demonstrate a mixed posting worked fixture and totals over all filters independent of pagination. For example: subsidiary-only A debit 100, detail B credit 100: at `detail` both must remain visible and totals debit=credit=100 if it is promised as a complete trial balance.
2. **BLOCKER — company owner invitation contradiction.** `POST /companies/{companyId}/members` allows existing company owner to invite a new email as `owner`, while `POST /auth/invitations/activate` says "Never creates owner". Clarify that authorized invitations may grant company-scoped owner membership to an activated new user, never global/super-admin privileges, OR expressly prohibit owner invitations to new addresses in both endpoints. Revalidate inviter permissions and immutable token binding atomically.
3. **BLOCKER — complete OpenAPI validation absent.** Validation evidence reports `js-yaml 4.1.0` PASS and substituted-OAI/Ajv2020 structural/schema syntax PASS (69 schema checks, 23 paths, 33 operations, 236 references). The untouched official OpenAPI 3.1 dialect evaluation is `NOT_PASSED` (329 errors), and documented Node CLI reproduction was not executed. Run an independent OpenAPI 3.1-compliant validator against unchanged blob; record validator version, executed command, output and exact SHA. Do not call a modified-dialect PASS unqualified specification conformance.
4. **Security implementation requirements (nonblocking contract review notes):** Session must use HttpOnly/Secure/SameSite, server-side company-membership authorization for every object (including invited company/role), origin-and-cookie-bound CSRF for unsafe methods including anonymous activation, rotation at authentication, token hash/expiry/single-use and transactional consumption; reject cross-company IDs with non-disclosing 404. All of this is design only; not penetration tested.
5. **Accounting implementation requirements (nonblocking notes):** IRR decimal strings parsed to Decimal, persisted as NUMERIC(20,0), no floats; POSTED-only ledgers, excluded drafts, linked reversals, transaction-safe exactly-once posting/numbering, period-close lock protocol and pre-pagination report totals. F1/F2/F3 plus mixed subsidiary/detail leaf fixture are essential eventual PostgreSQL/HTTP tests.

### Disposition and authorization boundaries
Readable and largely implementable contract shape, but **no explicit consumer acceptance** of this SHA due to the above blockers. Re-review after Coordinator revises and provides new final SHA. This is documentation review, **not** source implementation, independent QA, CI PASS, or Manager freeze. H-03 and W1 remain unauthorized. No application, contracts, TASKS/WAVES or other agents' files changed.


## 2026-11-14 — H-02 rc.3 read-only Developer consumer re-review

**Decision: APPROVED / ACKNOWLEDGED FOR CONTRACT CONSUMPTION ONLY** (not PR merge approval, runtime PASS, QA PASS, Manager freeze or W0 exit).
- Manager authorization: `APP-HESABYAR-W0-RC3-REVIEW-20261114-001`.
- PR: https://github.com/Ana0251/ChatGPT-Team-Test/pull/1
- Version: **`1.0.0-rc.3`**.
- Exact OpenAPI blob SHA checked directly against GitHub: **`98d34e7bd7b4551c0f429ea5e388781060ceaf63`**.
- PR head at verification: `586f7b70e6280264e9c423b540a2a2a4306b8cc4`.

### Resolved prior Developer blockers
1. **Detail-level trial balance:** `level=detail` is explicitly the complete posting-leaf set (DETAIL leaves and direct-postable SUBSIDIARY without DETAIL child), with actual `account_level` and `account_name`. Source rows are counted exactly once, and `TrialBalanceTotals` is calculated over authorized filtered population before pagination. `docs/contracts/TRIAL_BALANCE_FIXTURE.md` documents subsidiary A debit 100 and detail B credit 100, with two pages and shared totals 100/100. This resolves the rc.2 missing-leaf contract contradiction; the fixture is not an executed test.
2. **Company-owner invitation:** `/companies/{companyId}/members`, `/auth/invitations/activate` and `/auth/invitations/accept` now consistently allow a new principal to gain only the bound company's owner membership when a currently authorized existing owner issued the invite. Inviter authority is rechecked atomically; admins cannot issue owner invitations; no global or super-admin grant.
3. **CSRF / errors:** Anonymous pre-session and authenticated session CSRF binding, same-origin enforcement, rotation at login, safe one-time token refresh and human resubmission without blind mutation replay are specified. Stable `ErrorCode` and `FieldIssue` include JSON Pointer fields and zero-based `line_index`. `JournalWarning` is structured; journal totals are always present. `Movement` provides stable `line_id`, line_index, description and account metadata. Inclusive Jalali UI dates vs exclusive Gregorian API bounds are documented.
4. **Independent OpenAPI evidence:** `VALIDATION.md` and `validation-result.json` report actual execution of `@apidevtools/swagger-parser 11.0.0` vendor **schema-validation function** against *unchanged* rc.3 YAML, with PASS, source/version/SHA and qualified limitations. Supplemental js-yaml/Ajv checker reports 23 paths, 33 operations, 18 CSRF-protected mutations, 239 refs, 72 syntax checks, zero findings. Full async vendor dereference, Node CLI, unchanged OAI dialect resolution, CI, runtime HTTP/DB tests and independent QA are **NOT_RUN/NOT_PASSED as applicable**; this is adequate for the authorized contract-consumer review, not full specification/runtime certification.

### Reviewer disposition
**No remaining blocking consumer-contract finding** within the approved re-review scope. Explicit Developer acknowledgment of **only** `1.0.0-rc.3` / SHA `98d34e7bd7b4551c0f429ea5e388781060ceaf63`. Any subsequent OpenAPI blob change invalidates this acknowledgment and requires new review. A reproducible CI/OpenAPI gate, independent PR review, UI/UX acknowledgment, Manager freeze/W0 exit and main branch protection remain external gates. **H-03 and W1 remain unauthorized.** No product code, contract, other-agent reports or TASKS/WAVES modified.
