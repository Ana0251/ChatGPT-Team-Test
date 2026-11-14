# چک‌لیست بازبینی H-17 (بدون ادعای تست اجرایی)

**Contract:** `1.0.0-rc.3`, blob `98d34e7bd7b4551c0f429ea5e388781060ceaf63`. **Authorization:** `APP-HESABYAR-W1-ENTRY-20261114-001`. **Status keys:** `SPECIFIED` = covered in design text; `NOT_TESTED` = no runtime evidence; `FAIL` = failed actual inspection/test. Do not call SPECIFIED a runtime PASS.

| ID | Design inspection / expected acceptance | Design status | Browser/a11y status |
|---|---|---|---|
| RTL-01 | Shell Persian `lang=fa`, `dir=rtl`; headings/labels logical inline start | SPECIFIED | NOT_TESTED |
| RTL-02 | LTR isolation for email, UUID, codes and ISO; bidi punctuation stable | SPECIFIED | NOT_TESTED |
| THEME-01 | Light/dark semantic palette for surface/text/action/focus/status | SPECIFIED | NOT_TESTED |
| THEME-02 | Contrast text >=4.5:1 normal, >=3:1 large; UI/non-text >=3:1, all states | SPECIFIED | NOT_TESTED |
| TYPE-01 | Persian type scale, readable line heights and fallback fonts | SPECIFIED | NOT_TESTED |
| SPACING-01 | 4px scale; 44px touch controls, visible feedback | SPECIFIED | NOT_TESTED |
| MONEY-01 | Exact IRR strings, no float, 20-digit full-display, grouped Persian numbers | SPECIFIED | NOT_TESTED |
| MONEY-02 | Invalid fractions, negatives in unsigned amounts, overflow rejected visibly | SPECIFIED | NOT_TESTED |
| MONEY-03 | Codes retain leading zeros; missing ≠ zero; signed reporting explicit | SPECIFIED | NOT_TESTED |
| DATE-01 | Jalali display ↔ Gregorian date-only API, Tehran cutoff | SPECIFIED | NOT_TESTED |
| DATE-02 | Exclusive end converted to previous day for visible inclusive Persian end | SPECIFIED | NOT_TESTED |
| FORM-01 | Label/description/error and persisted form data on invalid submit | SPECIFIED | NOT_TESTED |
| ERR-01 | Localized ErrorCode/FieldIssue and focus to JSON Pointer/line_index | SPECIFIED | NOT_TESTED |
| DRAFT-01 | Incomplete drafts show warning; posting distinguishable and server-gated | SPECIFIED | NOT_TESTED |
| SECURITY-01 | CSRF refresh once; no unsafe automatic replay; explicit retry/re-login | SPECIFIED | NOT_TESTED |
| A11Y-01 | Keyboard-only operation, focus visible, logical order and dialog return | SPECIFIED | NOT_TESTED |
| A11Y-02 | Focus not hidden, buttons correctly named; errors announced | SPECIFIED | NOT_TESTED |
| A11Y-03 | WCAG 2.2 AA target size, motion reduction, 200% zoom/reflow | SPECIFIED | NOT_TESTED |
| RWD-01 | 360px width, one-column forms, wrapped controls, no clipped money | SPECIFIED | NOT_TESTED |
| RWD-02 | Tables allow discoverable scroll without hiding amounts/headers | SPECIFIED | NOT_TESTED |
| RWD-03 | 600px and 1024px breakpoints, focus/reading order preserved | SPECIFIED | NOT_TESTED |

## Evidence capture protocol
For future approved implementation review: record viewport 360/390/600/1024/1280, device pixel ratio, browser/version, light/dark, 200% zoom, keyboard-only path, screen reader/browser, contrast tool/version, screenshots with sensitive values redacted, observed result, PASS/FAIL, issue link. **No implementation exists in H-17, so all runtime rows remain NOT_TESTED**.

## Visual audit sign-off gate
- Confirm all four H-17 files in the PR are inside `design/tokens/**` or `design/specs/global/**`, with no `frontend/**`, `backend/**`, `docs/contracts/**`, task ledger or H-18 changes.
- Confirm money and date rules match frozen OpenAPI SHA, and components include keyboard/focus/error states.
- Reviewer can mark **specification completeness** after document inspection; runtime responsiveness, contrast, browser focus and AT acceptance require independent later checks.
- Manager must review PR and explicitly authorize merge; H-17 does not self-merge or self-complete official ledger.
