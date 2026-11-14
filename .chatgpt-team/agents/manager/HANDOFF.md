# manager / HANDOFF

## 2026-11-14 — H-02 follow-up: Coordinator fixes after both consumer reviews

**Next conversation:** Coordinator H-02, SAME PR https://github.com/Ana0251/ChatGPT-Team-Test/pull/1; do not activate any other agent yourself.

Manager decision: `APP-HESABYAR-H02-CONSUMER-FINDINGS-20261114-001` in DECISIONS and TASKS approvals; manager PR comment `6875071707`. Developer review comment `6875035147`, UI/UX review comment `6875039903`. Both consumers CHANGES_REQUIRED on OpenAPI `1.0.0-rc.2` blob `c7d45ebfb715aea6960f130648ebfde148c93e54`.

**Mandatory repairs, no new tasks:** 
1. `level=detail` trial balance complete for *all effective postable leaves*, including directly postable subsidiary without DETAIL child; expose actual account_level/account name, maintain stable totals independent of pagination; fixture subsidiary Dr 100 / detail Cr 100 => 100/100.
2. Allow **company-scoped** owner invitation/activation for new email when invitation is issued by existing company owner; never grant global superadmin. Align both invite and activation contracts/roles/security.
3. Stable error codes and structured `details` field paths; structured warning code/line_index for draft journal UX; line_id/description and account label/level for reports; CSRF token refresh and explicit user resubmit after failure; session expiry and Jalali half-open period display.
4. Independently validate unchanged final OpenAPI 3.1 YAML with a standards-conforming tool, exact executed command/version/output/blob SHA, no claims beyond evidence.
5. Update same PR/docs and own Coordinator report, bump prerelease contract version (suggest rc.3). Supply actual commit/openapi blob SHA and unresolved blockers. Do not modify other agents' reports or central ledgers, implement app/design, merge PR or authorize W1.

After Coordinator repairs, user returns Manager for renewed Developer/UI/UX read-only review of **final new exact SHA**, independent PR review, possible W0 freeze decision.

**Separate repository owner action:** enable GitHub protection for main (require PR/review; no force push/delete; required checks after CI exists). This is needed before W1 code merges and is not a substitute for H-02 corrections.
