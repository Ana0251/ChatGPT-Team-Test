# H-02 mixed posting-leaf fixture — 1.0.0-rc.3

**Normative scope:** authorized company X, open fiscal period `[2026-03-21,2027-03-21)`, no opening balances. In account chart: `A` = active SUBSIDIARY without DETAIL children, postable; `B` = active DETAIL leaf under another subsidiary, postable. One **POSTED** journal, same company, posting_date 2026-04-01: line 0 A debit `"100"`, credit `"0"`; line 1 B debit `"0"`, credit `"100"`. Drafts outside posted stream are ignored. Stable line_id generated per posted line.

Request: `GET /api/v1/companies/{companyId}/reports/trial-balance?level=detail&from_date=2026-03-21&to_date=2026-04-02&page=1&page_size=1`.

Expected full sorted *eligible* row set (across pages):
| Account | account_level | opening D/C | debit | credit | closing D/C |
|---|---|---|---:|---:|---|
| A / SUBSIDIARY (direct-postable) | subsidiary | 0 / 0 | "100" | "0" | "100" / "0" |
| B / DETAIL | detail | 0 / 0 | "0" | "100" | "0" / "100" |

Expected: `total=2`, `page_size=1`; page 1 has only A, page 2 only B; **both** responses include **identical** `totals` with `opening_debit="0",opening_credit="0",debit="100",credit="100",closing_debit="100",closing_credit="100"`. Each posted line maps to one and only one eligible row, irrespective of page. Actual `account_name` and `account_level` are required on every row. No parent roll-up rows in detail output.

For `level=subsidiary` the same journal aggregates B to its subsidiary parent and A to itself. For `level=general`, both map to their respective general ancestors. Each level totals exactly the same **movement** debits and credits when no additional account-level filters are applied. A selected detail view is *not* DETAIL-only; its UI label must say **"تمام حساب‌های قابل ثبت (تفصیلی و معین مستقل)"**.

**Other approved fixtures retained:** F1 posted movements Dr=Cr=`"1200000"`; F2 including posted reversal Dr=Cr=`"1400000"`; F3 cross-tenant object/code attempted access yields no disclosure (404), with no contribution to totals. The mixed fixture is an acceptance design, **not a claim that runtime, DB or QA tests have passed**.
