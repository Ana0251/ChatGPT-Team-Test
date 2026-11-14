# حسابیار — استاندارد عمومی UI/UX (H-17)

**Status:** PROPOSED FOR MANAGER REVIEW · **Owner:** UI/UX · **Decision:** `APP-HESABYAR-W1-ENTRY-20261114-001` · **Contract:** OpenAPI `1.0.0-rc.3`, blob `98d34e7bd7b4551c0f429ea5e388781060ceaf63`.

## 1. Scope and principles
This is a design specification only. No frontend implementation, service behavior, business-rule changes, workflow H-18, or new APIs are authorized. Financial accuracy, predictable feedback, accessibility, and legible Persian-first UI outweigh decoration. Dark/light themes shall have parity. The JSON token catalog in `../../tokens/foundations.json` is the proposed source for semantic visual values; it is **not** executable source.

## 2. Locale, direction and bidi
- App shell `lang=fa`, `dir=rtl`; navigation begins at the right. Labels and icon-text sequences are RTL; order of accounting columns remains explicit and consistent across modes.
- Use logical spacing and alignment terminology (`inline-start/end`, `block-start/end`), never assume `left` means start. Never reverse the semantic order of debit/credit, chronological time, or keyboard Tab sequence merely to mirror a layout.
- A Persian text block remains RTL. Email, UUID, account codes, ISO dates and other Latin tokens use isolated LTR runs (`dir=ltr`, `unicode-bidi:isolate`, `bdi` where suitable). Keep punctuation from jumping across numeric fragments; avoid mixed bidi text concatenation.
- Display digits may be Persian for localized labels and amounts, but **preserve code/identifier digit characters and leading zeros** exactly as recorded; use an isolated numeric run. Accessible name must convey the entire numeric value and unit.
- Calendar weekday headers and navigation must match Persian reading order; do not use mirrored arrow icons when the icon implies absolute time or a universal symbol. On directional controls, arrow direction must reflect actual chronological action and accessible label.
- Error text is an authored Persian translation of stable machine codes, never raw server English strings. Avoid revealing cross-company resource identities.

## 3. Typography and layout
- Proposed type stack: `Vazirmatn` (properly licensed at implementation time), then Tahoma, then system sans. No font binaries committed; graceful fallback must preserve Persian digits, diacritics, and numerals.
- Base 16px/1.75 for prose, input labels >=14px, caption 12px only for secondary short metadata (never critical financial values). Heading 28px/1.4, section 22px/1.4, subsection 18px/1.4. Avoid compressed letter spacing in Persian.
- Use 4px modular spacing (4/8/12/16/20/24/32/40/48/64), surface radius 8–16px. Dense data tables have at least 48px rows; controls >=44px high in touch contexts.
- Create consistent visual hierarchy: page title → contextual company/year bar (future H-18 supplies interaction) → toolbar → data/form region → status/action region. Do not implement company selector interactions in H-17.

## 4. Theme, palette and states
- Light and dark palettes are specified in the token catalog, keyed by semantic purpose, not hard-coded into future components. Background, surface, text, muted text, border, primary/action, focus, info, success, warning, and danger tokens required for each mode.
- Default light selection follows product setting; system preference may be used only after explicit product behavior is approved. Theme switch must not discard drafts or focus position. Avoid pure black and relying solely on green/red for debit/credit or validity.
- Contrast acceptance: normal text >=4.5:1; large text >=3:1; visible control boundaries, icons and focus indication >=3:1 against adjacent colors. Verify token combinations and hover/disabled/read-only states in both modes; token declaration alone is not an accessibility test.
- All semantic statuses combine icon/wording plus color. Focus ring 2px with perceptible offset and sufficient contrast; keyboard focus is never removed without an equally visible replacement.
- Status matrix: idle=neutral; loading=progress indicator with status message; success=confirmation with changed state; warning=amber + explicit next step; error=red + explanation and correction; disabled=reason available; read-only=content readable and no misleading enabled controls.
- No automatic disappearance of critical finance, permissions, or security errors; noncritical toast duration and pause behavior to be tested.

## 5. Base component contract (visual/state only)
| Component | Minimum specification | State and accessibility |
|---|---|---|
| Button | primary/secondary/tertiary/destructive; min 44px touch area; meaningful verb | default/hover/focus/pressed/loading/disabled; busy prevents repeat action |
| Text input | persistent label, optional hint, 44px height; no placeholder-only labels | normal/focus/invalid/disabled/read-only; `aria-describedby` for hint+error |
| Numeric/amount input | isolated numeric direction; visually align digits consistently; no silent precision loss | explicit unit ریال; formatted view vs editable raw value; validation near field |
| Date input | Jalali visual picker and editable localized display with Gregorian API boundary | keyboard text entry and clear error; screen-reader announcement of calendar date |
| Select/combobox | label and search optional, list state clear | keyboard arrows/Home/End/Escape, active item and result count announced |
| Checkbox/switch | clear checked/unchecked, descriptive label | semantic control type; never use a switch for destructive action |
| Dialog | short title, summary of consequence and explicit cancel/confirm | trap focus while open; return focus to trigger; Esc unless unsafe to dismiss |
| Alert/toast | status icon + clear Persian message; link to correction where useful | appropriate live region; never rely on color alone |
| Tabs | active indicator and underline; don't confuse with navigation links | arrow key movement per chosen tab pattern; focus and selection distinguishable |
| Table | labeled headings, numeric alignment, readable row selection | semantic table headers; keyboard focus; horizontal overflow not clipped |
| Pagination | current/total and first/previous/next/last localized | announce page and total; disabled ends explicit |
| Skeleton/progress | approximate real shape and text alternative | busy state announced; reduced-motion compliant |

Visual patterns are proposals for reusable primitives; implementation details and feature-specific flows belong to later approved tasks.

## 6. Forms, feedback, safety
- Required fields marked by text and programmatic required state; inline errors identify field and correction, with an error summary linking/focusing first invalid input. Preserve entries on validation failure.
- The frozen contract has `ErrorCode`, `FieldIssue.field` JSON Pointer and optional zero-based `line_index`; render translated error code/reason and focus corresponding control without exposing raw server messages.
- Incomplete/unbalanced drafts may be saved with structured warnings; posting must be clearly distinct, require backend acceptance, and never be represented as complete based on frontend totals alone.
- Prevent duplicate destructive/financial mutation clicks while pending; display pending/unknown outcome without falsely declaring success. For CSRF_INVALID obtain a new token **once** and require explicit human resubmission; never silently replay an unsafe request. On expired session require login and recheck company/year.
- Confirmation patterns require concise impact statement and an explicit destructive verb; read-only posted documents must not display editable affordances. Feature-specific screens are out of H-17 scope.

## 7. Responsive global layout
- **360–599px:** viewport padding 16px; single-column form; labels above inputs; full-width primary action when appropriate; cards stack; avoid fixed widths, clipped labels and nested scroll traps. Numeric rows may use a clearly labeled vertical summary; real tables allow a single explicitly discoverable horizontal scroll region, never hide financial columns silently.
- **600–1023px:** padding 24px; two columns only when each control retains readable space; toolbar wraps; no hard-coded sidebar forcing content below 360px.
- **>=1024px:** padding 32px, max content width 1280px; grid may expand to 2–3 columns; large accounting tables can use consistent sticky headings with correct z-index.
- At 360px viewport and 200% text zoom, no component must obscure critical controls; reflow content, allow long company names/amounts to wrap or scroll safely. Exceptions for inherently two-dimensional data are documented, not used to waive other reflow requirements.
- Minimum hit target 24x24 CSS px or sufficient spacing per WCAG 2.2 AA, product touch target **44x44px** wherever practical. Distinguish actual pointer target from visual icon size.

## 8. Design acceptance evidence
Review the checklist in `REVIEW_CHECKLIST.md`; all items must have explicit PASS/FAIL/NOT_TESTED and test width/theme/context. Specs-only inspection may confirm documentation completeness but cannot claim browser/screen-reader QA. Reviewers must link exact PR commit and cite unanswered questions. Any changes to API fields/security need Coordinator contract change and new SHA review; do not patch OpenAPI from UI/UX.
