# v1 triage outputs that conflict with the v1.1 rules

**v1.1, derived from v1 eval errors; not yet tested on a fresh eval set.**

- **What was checked.** All 215 v1 triage outputs in `data/triage/` (post-Stage-B), read
  against the v1.1 rules in `pipeline/triage_prompt.md` (section "v1.1 rules" and the
  `interpretation` change type).
- **How.** Each document's FR type, ACTION line, agency and title come from the committed
  metadata store. The v1 answer, change type and rationale come from its triage output.
  Nothing was re-triaged.
- **Unchanged.** This list changes no v1 output and no v1 score. Operational decisions on
  individual documents are made by human review (`records/REVIEW_LOG.md`).

## Relevance conflicts (5)

| Document | Title (short) | v1 answer | v1.1 answer | v1.1 rule |
|---|---|---|---|---|
| 2024-22962 (eval #25) | CFPB Reg F advisory opinion: medical debt | Relevant, 0.70, guidance | Not relevant | Guidance limited to a non-loan debt type. The opinion restates Regulation F provisions for medical debt and states no rule for consumer-loan collection generally. **Resolved by human review:** closed as not relevant (REVIEW_LOG). |
| 2024-27791 | CFPB Reg F advisory opinion: medical debt; revised applicability date | Relevant, 0.70, guidance | Not relevant | Same opinion as 2024-22962; this document only moves its applicability date. **Resolved by human review:** closed as not relevant to match the 2024-22962 override (REVIEW_LOG). |
| 2024-29292 | CFPB Reg V ANPR: identity theft and coerced debt | Relevant, 0.75, proposed_rule | Not relevant | ACTION line: "Advance notice of proposed rulemaking." The v1 rationale confirms there is no proposed text. ANPRs without proposed text are not relevant. Its record is open and awaits reviewer sign-off. |
| 2025-22490 (eval #12) | NCUA: remove 12 CFR 748 Appendix B (breach-response guidance) from the CFR | Not relevant, 0.75, proposed_rule | Relevant, `interpretation` | Legal-status change: guidance moved out of the CFR with its text unchanged. **Resolved by human review:** change record created (REVIEW_LOG). |
| 2025-22489 | NCUA: remove 12 CFR 748 Appendix A (Guidelines for Safeguarding Member Information) from the CFR | Not relevant, 0.75, proposed_rule | Relevant, `interpretation` | Same legal-status change as 2025-22490, for the safeguarding guidelines (DATA.PRIVACY_SECURITY). Published the same day by the same agency. **Not yet reviewed:** it is in the review queue (0.75 < 0.85) with no change record. |

## Change-type conflicts on relevant documents (4)

These documents stay relevant. Under v1.1 they route as `interpretation` (control validation)
instead of their v1 type. Step 4 applies this to their change records. The model outputs keep
their v1 type.

| Document | Title (short) | v1 change type | v1.1 change type | Why |
|---|---|---|---|---|
| 2024-24093 | Supervisory Highlights: Auto Finance | enforcement_signal | interpretation | Supervisory findings interpret existing obligations. |
| 2024-30758 | Supervisory Highlights: Student Lending | enforcement_signal | interpretation | Same. |
| 2024-31670 | Supervisory Highlights, Issue 37 | enforcement_signal | interpretation | Same. |
| 2025-19671 | CFPB interpretive rule: FCRA preemption of state laws | guidance | interpretation | Interpretive rule: states how existing FCRA preemption applies, without changing rule text. |

2024-22962 and 2024-27791 would also move from `guidance` to `interpretation` if they were
relevant. They are listed above as relevance conflicts instead.

## Checked and consistent (near the line)

These v1 answers agree with v1.1. They are listed because a v1.1 rule speaks to them
directly.

| Document | v1 answer | v1.1 rule that confirms it |
|---|---|---|
| 2025-04811, 2025-17898, 2025-22063, 2025-10998, 2025-15809, 2026-13874, 2026-18366, 2026-09134, 2024-21642 | Not relevant | Who it binds: blocking, authentication and database duties fall on voice service providers, not on callers. |
| 2024-24908, 2025-16641 | Not relevant | Prior express written consent applies to telemarketing only (marketing-only exclusion). 2025-16641 conforms the rule to the court vacatur of the one-to-one consent rule. |
| 2026-17774, 2025-21323 | Not relevant | FCC dismissals of old TCPA petitions leave covered rules unchanged. These are not a "final decision terminating a covered proposal": petitions are not proposed rule text. |
| 2025-15089, 2025-15091, 2025-15088, 2025-16139, 2026-04907, 2026-04952, 2026-07473 | Not relevant | ANPRs without proposed text. |
| 2025-14060 | Not relevant | General review (EGRPRA), typed "Proposed Rule". The ACTION line decides. |
| 2025-11280, 2025-21333, 2025-23712, 2026-13834 | Not relevant | Requests for information. 2026-13834 is typed "Proposed Rule". |
| 2026-16615, 2026-16617 | Not relevant | Regulatory agendas, including the Unified Agenda. |
| 2025-01142, 2024-27458, 2025-11410, 2025-18398, 2026-01557, 2026-10099 | Not relevant | Paperwork information collections. |
| 2026-08944 | Not relevant | Bank ownership and control notice. |
| 2025-19942 | Not relevant | Wholesale interbank payment operations (Fedwire, NSS). |
| 2025-08644, 2025-08645 | Relevant, withdrawal | Final decisions terminating covered proposals (2024-28690, 2025-00633). They close those records (step 3). |
| 2025-08286 | Relevant, withdrawal | The list of withdrawn items includes covered guidance, including 2024-22962 (item 3). |
| 2026-18852, 2026-18859 | Relevant, guidance | Proposed guidance with text, binding banks and credit unions on third-party vendor oversight. Not "a request for comment without proposed text". |
| 2025-00381 | Not relevant, withdrawal | Rescinds an advisory opinion on whether earned wage access is credit. None of the withdrawn content concerns consumer-loan servicing behavior. Left as is, but close to the line. |
