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
