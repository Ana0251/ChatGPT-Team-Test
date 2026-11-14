# نمایش عدد، پول و تاریخ در حسابیار — H-17

**Scope:** global presentation/input policy, not accounting algorithms or backend implementation. **Base:** H-D04/H-D05; OpenAPI `1.0.0-rc.3` SHA `98d34e7bd7b4551c0f429ea5e388781060ceaf63`.

## Numbers and exact monetary values
1. API money is a **decimal string of whole IRR rials** (`Rial` and signed reporting `SignedRial`), 1–20 digits, no decimal places. Never parse it with JS `Number` or other binary floating-point type for formatting, comparison or arithmetic. A future implementation should use a lossless string/BigInt/decimal-safe library; no conversion to tomans is automatic.
2. In read-only presentation group thousands with Persian comma `٬`, use localized Persian digits consistently, and append **ریال** in a separated, readable unit (example API `"1200000"` → `۱٬۲۰۰٬۰۰۰ ریال`). Maintain a programmatic accessible name that includes unit and complete amount. Provide enough room for the 20-digit maximum (wrap or contained horizontal scroll; never truncate money without an explicit reveal).
3. In editable controls, accept Persian/Arabic/ASCII digit entry, normalize to ASCII **only at submission boundary** after validation; allow grouping separators while typing but remove them for canonical API payload. Reject minus signs in unsigned debit/credit, fractions, exponent syntax, currency symbols, implicit rounding, and values with >20 digits. No leading-zero mutation for **account codes**; monetary leading zeros normalize only as documented by the API's canonical numeric pattern.
4. Amount input: right-aligned per RTL form layout, with an isolated LTR numeric editing run if required for stable caret movement and keyboard order. Label `مبلغ (ریال)`, hint `فقط عدد صحیح`. Explain error and preserve user input; avoid realtime formatting that moves caret on every key.
5. Debit and credit must remain **separately labeled** and explicitly noninterchangeable. Do not communicate meaning only by green/red. Show `۰ ریال` for known zero; use `—` with accessible label `داده موجود نیست` for missing/unknown, never conflate blank with zero. Negative signed balances use true minus with understandable debit/credit convention; do not round totals.

## Calendar and timezone
1. **User date inputs and labels:** Jalali calendar (e.g., `۱۴۰۵/۰۱/۱۲`); accessibility includes date in words if needed. API and DB date-only values: ISO Gregorian `YYYY-MM-DD`. Convert Jalali local date to Gregorian date-only *without timezone offset changes*. Never pass a displayed Jalali string to API.
2. Fiscal period and report windows are **half-open** `[start_date,end_date)` and `[from_date,to_date)`. Visible Persian end date is inclusive: subtract one Gregorian **calendar day** from exclusive API `end_date/to_date`, then convert to Jalali. When user selects inclusive Jalali last day, convert it to Gregorian, add exactly one calendar day, submit as exclusive end.
3. Validate Gregorian canonical from < to and period membership server-side; UI may show correction before submit but never assert closed/open state solely from local clock. Financial boundary uses `Asia/Tehran`; audit event timestamps are UTC and formatted in the viewer's authorized business context with timezone label.
4. Persian input digits may be normalized for display/entry, but API dates stay ASCII ISO. Example: display visible period `۱۴۰۵/۰۱/۰۱ تا ۱۴۰۵/۱۲/۲۹` for API `[2026-03-21,2027-03-21)` **only if the Jalali conversion library confirms this mapping**; never hard-code year-end/leap conversion by assumption.
5. Typed calendar errors must name the invalid field. Calendar dialog must support keyboard navigation, focus return and screen-reader cell labels; layout must fit 360px without horizontal clipping.

## Numeric text and assistive technology
- Use bidirectional isolation around UUIDs, ISO dates, amounts and mixed Persian/English labels. `tabular-nums` may improve column scanning when supported by chosen font; do not rely on font feature as a data integrity control.
- Always provide machine-readable raw values when practical for copying; copy action should preserve exact numeric digits and unit declaration. Avoid copying localized separators into raw API identifiers.
- State changes that alter totals are announced in text, with the raw unit and a link to review, not a color flash.
