# Hesabyar — HTTP Contract V1.0 (H-02)
**Status:** proposed / review pending. **Contract version:** 1.0.0-rc.1. **HTTP base:** /api/v1.
The machine-readable baseline is [openapi.yaml](./openapi.yaml); architecture rules are in ../architecture/README.md and ../architecture/OWNERSHIP_AND_REVIEW.md. No endpoint exists yet. Backend/Frontend implementation remains blocked by wave authorization.

## Compatibility and conventions
- All requests/response JSON UTF-8 with English API property names, Persian presentation only in frontend. ISO Gregorian dates, UTC event timestamps and exact IRR string amounts.
- Session cookie is secure, HttpOnly, SameSite and scoped to the service; CSRF token required for modifying requests (including login/logout as applicable), same-origin CORS preference. Cookie-based auth requires both active session and tenant membership; no client-supplied role or company trust.
- Tenant context is URL-scoped /companies/{companyId} wherever relevant; backend validates membership with each action. No default-cross-company reporting.
- Standard error: `{error:{code,message,details?,request_id}}`. 400 malformed business input, 401 unauthenticated/expired, 403 insufficient role or CSRF, 404 absent or nonvisible resource (do not leak cross-tenant IDs), 409 duplicate/period/state/idempotency conflict, 422 structural/domain validation; avoid leaking internals.
- IDs are UUIDs; list endpoints use cursor? Current baseline uses page/page_size with stable ordering and deterministic ties by id. Business rows are immutable once posted; request header Idempotency-Key mandatory on posting/reversal. Header CSRF token on all mutations.
- Roles: owner/admin can maintain memberships and company; owner/admin/accountant can maintain fiscal/accounts/drafts and post/reverse under policy; viewer read-only. Closing fiscal periods is owner/admin only. API enforces roles, not just UI.
- F1/F2/F3 are contract acceptance examples (in architecture). Posted-only reports include reversals, exclude drafts, and provide money as strings. Running totals sign convention: debit-positive; credit-negative; credit side displayed separately where needed.
- Proposed reference response paging: `{items:[],page:1,page_size:50,total:0}`. Max page size 100. Error `request_id` correlates sanitized logs without exposing credentials.

## Review evidence still required
- [ ] Developer consumer acknowledgment with exact contract SHA
- [ ] UI/UX consumer acknowledgment with exact contract SHA
- [ ] Security/accounting review and Manager freeze
- [ ] Future implementation conformance, PostgreSQL fixtures, CI and QA; nothing marked passed here

## Version change protocol
See ../architecture/OWNERSHIP_AND_REVIEW.md. Keep /api/v1 stable after freeze. Additive optional changes => minor; breaking behavior => major URL-version migration; docs-only => patch. Reviewer must verify breaking-change impact and regeneration of typed frontend client by H-21 authorized owner only.
