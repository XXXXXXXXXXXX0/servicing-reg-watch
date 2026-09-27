# v1 triage outputs that conflict with the v1.2 scope expansion

**v1.2 scope expansion, after the v1 eval; not measured by it.**

- **What was checked.** All 215 v1 triage outputs in `data/triage/` (post-Stage-B), against
  the v1.2 section of `pipeline/triage_prompt.md`: dispute and chargeback obligations that
  bind bank and credit-union customers are relevant even under card or deposit-account
  rules (the deposit-account exclusion is narrowed), plus Holder Rule claims and defenses,
  record retention, and payoff quotes and title or lien release after payoff.
- **How.** The committed GovInfo full text of each document was searched for the v1.2
  topics (error resolution, 1005.11, 1005.33, 1026.13, billing error, chargeback, claims
  and defenses, 1026.12(c), Holder Rule, record retention sections, payoff, lien or title
  release, Military Lending Act, Red Flags). 31 documents had a hit; each was read at the
  hit and compared with its v1 answer and rationale. Nothing was re-triaged.
- **Unchanged.** This list changes no v1 output, no eval label and no eval score.
  Operational decisions (reopening an auto-closed document) are for human review
  (`records/REVIEW_LOG.md`).

## Relevance conflicts (3)

| Document | Title (short) | v1 answer (route) | v1.2 answer | Why |
|---|---|---|---|---|
| 2024-29699 (eval sample; label N unchanged) | CFPB final rule: Overdraft Lending, Very Large Financial Institutions | Not relevant, 0.85 (auto-closed) | Relevant | The rule brings covered overdraft credit at banks and credit unions over $10 billion under Regulation Z's credit card provisions, including cardholder claims and defenses against the issuer (1026.12(c)) and billing-error handling. Those are dispute obligations binding bank and credit-union customers, which v1.2 no longer excludes as deposit-account rules. Note: the committed store holds no later document on this rule's status; whether it is still in force was not checked here and must be confirmed before any record is opened. |
| 2025-00565 | CFPB proposed interpretive rule: Regulation E and emerging payment mechanisms | Not relevant, 0.80 (review queue) | Relevant, low confidence | The proposal interprets which accounts and "funds" Regulation E covers, and so which accounts carry 1005.11 error-resolution duties. It is aimed mainly at nonbank payment apps; whether it changes any bank or credit-union dispute obligation is not settled by the text read. Already in the review queue. |
| 2025-08646 | CFPB withdrawal of 2025-00565 | Not relevant, 0.80 (review queue) | Relevant, low confidence (as a withdrawal) | Follows 2025-00565: if the proposal is relevant under v1.2, its withdrawal closes that record. Already in the review queue. |

## Class conflicts on documents already relevant (1)

| Document | Title (short) | v1 classes | v1.2 addition | Why |
|---|---|---|---|---|
| 2024-30758 | Supervisory Highlights: Student Lending | primary NEGOTIATION.TREATMENT, ACCOUNT.MODIFICATION, STOP.TRIGGERS (record_meta.yaml) | `DISPUTES.CLAIMS_DEFENSES` (primary) | Findings that servicers deceptively told borrowers whose contracts carry the holder notice that they could not assert claims and defenses against the holder. v1 had no class for this. |

## Checked, no conflict (selected)

- 2024-22004 (remittance disclosures, proposed): adds agency contact information to
  remittance disclosures, including the error-resolution notice form; it does not change
  how an error is handled. Not relevant under v1.2 either.
- 2024-25079 (Section 1033 open banking, eval): error-resolution text concerns Regulation E
  and Z interplay for data access; open banking stays excluded.
- 2024-27836 (larger participants, digital payment apps, eval): changes who the CFPB
  supervises among nonbank payment apps, not a bank or credit-union dispute obligation.
- 2024-31670 (Supervisory Highlights Issue 37, relevant): "chargeback" appears only as
  context for a stop-payment finding against card networks; no new class.
- 2024-24093 (Supervisory Highlights Auto Finance, relevant): payoff, GAP and total-loss
  findings are already covered by its classes; they now also back register rows
  UDAAP-PAYOFF-001 and UDAAP-INS-001.
- The remaining hits (FCC, capital, AML, fee rules and others) were incidental uses of
  the search terms.
