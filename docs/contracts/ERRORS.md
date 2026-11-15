# H-02 API error and warning taxonomy — 1.0.0-rc.4

## Envelope / localization and focus
All errors use `{ "error": {"code":"...", "message":"...", "request_id":"...", "details":[{"field":"/lines/0/account_id","line_index":0,"reason":"NOT_POSTABLE","message":"..."}]}}`. `code` and `reason` are stable English machine values; UI translates them to Persian via localized resources, **never** parses English or Persian `message`. `field` is a JSON Pointer to the submitted DTO; `line_index` is zero-based and refers to the exact submitted/persisted current line order. Optional `details` is [] or omitted for non-field errors; `request_id` is for support trace, not authorization. Do not emit credentials, raw invitation/setup/CSRF tokens, tenant identity hints or SQL details. HTTP 404 intentionally also covers invisible cross-company resources. Invalid input (422) uses per-field details and focus; unchanged user data is retained.

| HTTP | Stable error.code | Operations/examples | UI / machine response |
|---|---|---|---|
| 401 | AUTH_INVALID | POST /auth/login (invalid email/password) | Generic invalid credentials, no account enumeration |
| 401 | SESSION_EXPIRED | /auth/me, authenticated POST/PATCH/DELETE, invitation accept, journal posting | Clear authenticated state, prompt new login; preserve local unsent form in-memory only |
| 403 | ACCESS_DENIED | all protected resources / insufficient membership or role | Permission banner; never retry as another tenant |
| 403 | CSRF_INVALID | all unsafe methods incl. anonymous activation/login, journal writes and invitation acceptance | Follow CSRF recovery below, not auto-replay |
| 404 | RESOURCE_NOT_FOUND | all tenant resource paths with missing or unauthorized ID | Do not reveal whether other company contains identifier |
| 409 | INVITE_EXPIRED, INVITE_INVALID, INVITE_ALREADY_USED | /auth/invitations/accept and /auth/invitations/activate | Show neutral message; ask inviter to reissue, never reveal target email |
| 403 | INVITE_ROLE_FORBIDDEN | POST /companies/{companyId}/members (admin invites owner; revoked inviter authority) | Preserve selection; only current company owner can invite owner |
| 409 | DUPLICATE_MEMBERSHIP | invitation acceptance; company membership invite | No double-create, redirect to permitted current membership |
| 409 | INVITE_RATE_LIMITED | POST /companies/{companyId}/members: rolling 24-hour invitation quota reached (20 successful invitations per issuer/company or 50 per company) | Show a neutral, localized invitation-limit message without revealing company or recipient details. Explain that the quota is temporarily exhausted; wait until capacity becomes available in the rolling 24-hour window, then review the request and submit it **manually**. Do not automatically retry, replay the POST or expose quota history from another tenant. |
| 409 | PERIOD_CLOSED | POST /journals/{journalId}/post, reverse; period closure race | Show chosen period closed; no blind repost |
| 409 | PERIOD_OVERLAP | fiscal-year/period create | Highlight /start_date and /end_date |
| 422 | INVALID_DATE_RANGE | fiscal-year/period create and reports with to_date <= from_date | Focus date inputs, show exclusive end |
| 422 | ACCOUNT_NOT_POSTABLE | journal post, account pick validation | Field /lines/{i}/account_id, reason NOT_POSTABLE and line_index i |
| 409 | ACCOUNT_IN_USE | account delete/mutation | Explain posted references prevent deletion |
| 422 | UNBALANCED | journal post | Totals don't match, reason NOT_BALANCED |
| 422 | JOURNAL_LINE_INVALID | journal post | Details /lines/{i}/debit etc., reason INCOMPLETE/INVALID |
| 409 | JOURNAL_IMMUTABLE | posted journal update/delete | Read-only post state, guide reversal |
| 409 | DUPLICATE_POST | repeat post of already-posted document | Show canonical posted document |
| 409 | IDEMPOTENCY_CONFLICT | same key reused for different post/reverse payload | Do not silently repeat; require user review |
| 422 | VALIDATION_ERROR | any malformed field, page, name, money | Field issues reason REQUIRED/INVALID/TOO_LARGE etc. |

Other machine reasons: `NOT_FOUND`, `OUTSIDE_PERIOD`, `CLOSED`, `MISMATCH`, `DUPLICATE`, `EXPIRED`, `FORBIDDEN`, `NEGATIVE_OR_FRACTIONAL`. No unspecified catch-all codes exposed beyond published enum without contract update. All referenced statuses/codes are normative: schema includes corresponding responses for operations in its declared scope.

## Journal warnings
`Journal.warnings` is `JournalWarning[]` (never plain strings), each with `code`, optional `field` JSON Pointer and `line_index`, plus safe `message`. Codes: `DRAFT_INCOMPLETE`, `DRAFT_UNBALANCED`, `LINE_MISSING_ACCOUNT`, `LINE_MISSING_AMOUNT`, `LINE_ACCOUNT_NOT_POSTABLE`, `LINE_AMOUNT_INVALID`, `DRAFT_DATE_OUTSIDE_PERIOD`. Draft saving is allowed despite these warnings as long as supplied IDs stay company-scoped. `Journal.total_debit` and `total_credit` are **always** returned, even for incomplete drafts, by summing valid supplied whole-rial amounts (missing fields count as 0 for draft totals; invalid supplied amounts are rejected as 422). Posting fails with structured errors unless fully balanced, two valid lines, open period and current authorization.

## CSRF recovery state machine — no automatic mutation replay
1. **Before any unsafe request**: GET /auth/csrf (Cache-Control no-store) with bound cookie and same origin; display forms only after obtaining a usable CSRF token or show an actionable connection/security error; token stays in memory, not URL/localStorage.
2. **403 CSRF_INVALID**: Freeze the attempted mutation and keep user-entered form data locally. One **GET /auth/csrf** refresh is permitted to obtain a newly bound token. **Do not automatically retry** the original POST/PUT/PATCH/DELETE or reuse stale token; show localized action `Security token refreshed — check details and submit again`.
3. **If refresh fails / repeated 403**: Stop. Show explicit `Unable to verify secure session` recovery panel; let user manually refresh page or log in; do not silently discard form or issue another unsafe request. Do not loop.
4. **401 SESSION_EXPIRED** or /auth/me 401 on recovery: require re-login; after authentication session rotates, GET /auth/csrf again, re-check company and selected fiscal period and require **explicit human resubmission**. No duplicate posting: preserve idempotency key only for same unchanged body and confirmed same authorized company; if inputs changed create new key after user review.
5. Anonymous pre-session expired: fetch anonymous GET /auth/csrf once, then allow user to submit login/activation manually. Expired invitation tokens cannot be fixed by CSRF refresh. No tokens/passwords in logs or toast details.

## Jalali and exclusive ranges
All JSON `date` values and query filters are **Gregorian ISO** `YYYY-MM-DD`, timestamps UTC; business cutoff Asia/Tehran. Report interval `[from_date,to_date)`, so UI Persian *inclusive end* label must convert Gregorian `to_date - 1 day` to Jalali for display. To submit an inclusive Jalali end chosen by the user, convert that date to Gregorian then add one day to `to_date`. Fiscal period stored as start inclusive, end exclusive; its UI visible last date is `end_date-1 day`. Prevent off-by-one and DST errors using dates, not timestamps.
