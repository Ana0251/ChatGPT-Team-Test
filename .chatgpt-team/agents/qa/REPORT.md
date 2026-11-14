# qa / REPORT

## 2026-11-14 — H-18 independent documentation QA — PR #17

- **Result:** PASS LIMITED — documentation/specification review ONLY. This is not a runtime/browser/accessibility/security PASS, nor formal acceptance or merge authorization.
- **Framework:** 1.3.0. Legacy route: UI/UX owner → Coordinator → independent QA → Manager. Coordinator review: [PR #17 comment 6879398410](https://github.com/Ana0251/ChatGPT-Team-Test/pull/17#issuecomment-6879398410), PASS LIMITED.
- **Reviewed PR HEAD:** `8730866fde49dd61c7f66b85937d020771875e51` (open, unmerged before this QA report write). **Frozen contract** `docs/contracts/openapi.yaml`, version `1.0.0-rc.3`, blob `98d34e7bd7b4551c0f429ea5e388781060ceaf63`.
- **Authorized work:** H-18 `start_authorized=true`, dependencies H-02/H-17 `COMPLETED`, W1 entry authorized. H-18 ledger remains `AUTHORIZED_NOT_STARTED`; no ledger/state change by QA. H-26 not started.

### Evidence read (GitHub contents, static/manual comparison)
1. `design/specs/identity/AUTH_AND_INVITATIONS.md` blob `9cbad5b4de738a854320502633f254aa69f32ec8`.
2. `design/specs/identity/SESSION_STATES.md` blob `f7b52bc764d839782a74d4ba064c13c8fdf1643c`.
3. `design/specs/company-period/COMPANY_FISCAL_SELECTION.md` blob `3a07553adb7762803023906ab9bf87ebf1f3bf39`.
4. `design/specs/company-period/STATE_MATRIX_AND_REVIEW.md` blob `42009cf5aace6b14bf34cec30eef9592e7e3f7b2`.
5. Main: QA role/prompt 1.3.0, TASKS/WAVES/DECISIONS, H-17 `DESIGN_SYSTEM.md` and `REVIEW_CHECKLIST.md`, frozen OpenAPI, PR #17 changed paths and Coordinator review.

### Acceptance traceability (document inspection results)
- **ID-01–ID-08 (8/8 SPECIFIED):** internal email/password login, CSRF pre-auth and renewal, `/auth/me`, logout, 401/403/422, expiry, provisioning of first owner, invitations for new/existing users, pending invite status and owner-only company-scoped owner invitations. OpenAPI methods/response codes and CSRF/security constraints match at documented level.
- **CP-01–CP-06 (6/6 SPECIFIED):** membership-scoped companies, company-local role, explicit switch/clear context, no companies/years/periods, open/closed period, Gregorian exclusive end to Jalali inclusive previous calendar day. Relevant frozen API schemas and paths were inspected.
- **UI-01–UI-04 (4/4 SPECIFIED):** Persian RTL with LTR isolation, light/dark tokens, single-column 360px / 16px padding / >=44px targets, keyboard/focus/screen-reader/reflow/200% zoom and reduced-motion requirements referenced to H-17.
- **GOV-01 (1/1 SPECIFIED):** prior to this QA report commit, PR #17 changed four H-18 design files and the UI/UX owner's role report only. No edits to `frontend/**`, `backend/**`, frozen OpenAPI or task/wave ledgers. This QA role report is an additional, separately authorized report path.
- **Cross-screen matrix:** login, session, invitation, activation, company, fiscal year, fiscal period; Loading/Empty/Error/Permission Denied/Success cases defined. `SPECIFIED` is not a tested PASS.

### Follow-up items (not blocking documentation-only acceptance)
- Implement company-switch cancellation / request-generation gating and company-keyed caches so late in-flight responses cannot restore previous-company data.
- Prove invitation/setup token handling never creates token-bearing URLs, browser history, logs or persistent storage; use secure manual entry or compliant delivery. Verify error messages don't reveal membership.
- Execute future UI/browser at 360/390/600/1024, light/dark, 200% zoom, keyboard/focus, screen reader, reduced motion, localization and actual error/empty/loading/permission states.
- Independently test actual session/CSRF/401/403/404/409/422, role restrictions, invitation lifecycle and tenant isolation on implemented server. Verify no mutation retry after uncertain network response.

### Limitations and disposition
- **Documentation completeness: PASS LIMITED** (manual static GitHub file/contract cross-check; 19/19 design scenarios are specified).
- **Browser/rendering/360px/screenshots, two-theme actual contrast, keyboard/screen-reader, runtime API, actual auth/CSRF/tenant/security tests: NOT_TESTED.** No executable commands were run, and no runtime PASS is claimed.
- This recommendation applies to the four exact document blobs and the pre-QA PR head above. Any substantive design/API change requires re-review. Coordinator's earlier limited review is not treated as independent QA evidence.
- **Manager decision required:** accept design specification scope only or request further changes; keep PR #17 open, do not mark H-18 COMPLETED or merge based on this report alone.
