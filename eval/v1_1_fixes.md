# v1.1 fixes

**v1.1, derived from v1 eval errors; not yet tested on a fresh eval set.**

The v1 scores in `eval/results.md` are final and were not changed. Relevance triage was not
re-run. The v1 triage outputs in `data/triage/` and `data/triage_stage_a/` are unchanged and
still validate against the v1.1 schema. The fixes below change the instructions for future
triage runs only. Whether they improve precision or recall is unmeasured until a fresh eval
set is labeled and triaged. Re-scoring the 30 documents they were derived from would be
circular.

Root-cause codes follow `eval/error_analysis.md`: (a) prefilter drop; (b) gap in the
relevance test; (c) document-structure handling; (d) scope misapplied in triage;
(e) genuinely borderline.

## Error 1: FR 2025-22490 (eval #12), false negative

- **Document.** NCUA proposed rule to remove Appendix B (breach-response guidance) from
  12 CFR 748 and reissue its content as a Letter to Credit Unions.
- **Label.** Relevant, DATA.PRIVACY_SECURITY.
- **v1 answer.** Not relevant, 0.75. Stage A had said relevant (0.6); Stage B reversed it.
- **Root cause: (b).** The relevance test covered *withdrawn* guidance but said nothing about
  guidance moved out of the CFR with its text unchanged. Stage B used the document's own
  "no substantive change" statement as the test.
- **Fix** (`pipeline/triage_prompt.md`, "v1.1 rules"): "A change in an obligation's legal
  status is relevant even if its text is unchanged: codifying it, moving it out of the CFR
  into guidance or back, or removing it. Route these as change_type interpretation for
  control validation." `interpretation` is added to the `change_type` enum and defined, with
  the required action stated as control validation.

## Error 2: FR 2024-22962 (eval #25), false positive

- **Document.** CFPB advisory opinion on medical-debt collection under FDCPA / Regulation F.
  It was withdrawn by 2025-08286.
- **Label.** Not relevant.
- **v1 answer.** Relevant, 0.70 (guidance; PAYMENT.FEES, NEGOTIATION.TREATMENT,
  DISCLOSURE.REQUIRED).
- **Root cause: (b).** Advisory opinions counted as clarifying whenever they interpret an
  obligation within the test. Regulation F governs loan collectors too, so the model's call
  followed the prompt. Nothing excluded guidance aimed at a non-loan debt type or guidance
  that only restates existing law.
- **Fix** (`pipeline/triage_prompt.md`, "v1.1 rules"): "Guidance limited to a non-loan debt
  type, such as medical debt, is not relevant unless it states a rule that applies to
  consumer-loan collection generally. Guidance that only restates existing law routes as
  interpretation, not as a behavior change."

## Behavior-class tagging (from the class-agreement result: exact match 2/5)

- **Observation.** On the 5 true positives, the model predicted 17 classes against 14
  labeled; 5 predicted classes were unlabeled. Examples: INSURANCE.CLAIMS and
  DATA.PRIVACY_SECURITY on 2024-30824; PAYMENT.FEES and DISCLOSURE.REQUIRED on 2025-00633.
  These are classes a document touches without changing what the agent must do.
- **Fix.**
  - `pipeline/triage_prompt.md`: tags split into `behavior_classes_primary` (the document
    changes or clarifies what the agent must do; drives routing and review) and
    `behavior_classes_secondary` (touched, obligations unchanged; context only). When
    unsure, tag secondary rather than drop.
  - `pipeline/triage_schema.json`: holds both lists. v1's single `behavior_classes` list is
    still accepted so v1 outputs keep validating. API mode sends the v1.1 shape only.
  - `pipeline/triage.py`: validation requires a non-empty primary list when relevant, bars a
    class from appearing in both lists, and bars mixing the v1 and v1.1 shapes.
    `class_tags()` reads either shape; a v1 list reads as primary.
  - Change records now print primary and secondary classes on separate lines.
  - Tests: `test_v1_1_primary_secondary_tags` and schema/API-schema assertions.

## Other gaps checked

| Place | Contributed? | Finding | Fix |
|---|---|---|---|
| `PREFILTER.md` / `pipeline/prefilter.py` | No | Both documents were kept (rule A: 12 CFR 748 and 12 CFR 1006). Prefilter recall was 6/6. | None. |
| Triage prompt: read-through sentence under the "Not relevant unless" list | Yes, #25 | "A document in one of these areas is relevant if some part of it meets the test" let a Regulation F restatement count, even though the opinion applies it only to medical debt. | The sentence now says the read-through does not override the v1.1 non-loan debt rule. A part that restates a general provision while applying it only to a non-loan debt type does not meet the test. |
| Stage B partial reads (1,500 of 2,179 words for #12; 4,000 of 11,228 for #25) | No | The unread part of #12 repeats "no substantive change"; #25's call already rested on part III.A, which Stage B read. | None. |
| Federal Register type label | No | #25 is labeled "Rule" but its ACTION line says "Advisory opinion"; v1 recorded `guidance`, so it used the ACTION line. The step-2 rules state this explicitly. | See step 2. |
| Change type for guidance that restates law | Yes, #25 (exposed) | v1 had no type for "restates existing law." The #25 record therefore told the agent what it "must now do" as if the opinion changed conduct. | `interpretation` change type (control validation); applied to records in step 4. |
| Later withdrawal not reflected | Exposed by #25, not causal | #25 was withdrawn by 2025-08286, but its record still asked for implementation. This did not cause the relevance error: the label is N because of the medical-debt scope. | `supersedes` / `superseded_by` on change records (step 3). |
| Routing | No; it worked | #12 was not auto-closed (0.75 < 0.85), so the miss reached the human review queue. | None. |
