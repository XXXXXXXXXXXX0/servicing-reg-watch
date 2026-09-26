# Review log

Human review decisions that override the model's triage answer. They apply to the
operational records only:
- The model's original outputs (`data/triage/`, `data/triage_stage_a/`) are unchanged.
- The v1 eval scores in `eval/results.md` are unchanged.

Each override is also stored as a `review` entry in `records/record_meta.yaml`, which
`python -m pipeline.records annotate` applies to the record.

| Date | Document | Model answer (v1 triage) | Reviewer decision | Reason | Reviewer | Record |
|---|---|---|---|---|---|---|
| 2026-09-26 | [2025-22490](https://www.federalregister.gov/documents/2025/12/11/2025-22490/guidance-on-response-programs-for-unauthorized-access-to-member-information-and-member-notice): NCUA, Guidance on Response Programs for Unauthorized Access to Member Information and Member Notice (proposed rule; eval #12) | Not relevant, confidence 0.75, change_type proposed_rule, no classes (Stage B reversed a Stage A "relevant" at 0.6) | Relevant. Change record created with change_type `interpretation` (legal-status change; control validation) and primary class DATA.PRIVACY_SECURITY. | Change in an obligation's legal status: the breach-response guidance moves out of 12 CFR 748 into a Letter to Credit Unions with its text unchanged. | Angela | [2025-22490.md](2025-22490.md) (open; awaits control-validation sign-off) |
| 2026-09-26 | [2024-22962](https://www.federalregister.gov/documents/2024/10/04/2024-22962/debt-collection-practices-regulation-f-deceptive-and-unfair-collection-of-medical-debt): CFPB, Debt Collection Practices (Regulation F); Deceptive and Unfair Collection of Medical Debt (advisory opinion; eval #25) | Relevant, confidence 0.70, change_type guidance, classes PAYMENT.FEES, NEGOTIATION.TREATMENT, DISCLOSURE.REQUIRED | Not relevant. Change record closed after human review (sign-off filled). | Guidance limited to medical debt, a non-loan debt type. | Angela | [2024-22962.md](2024-22962.md) (closed) |
