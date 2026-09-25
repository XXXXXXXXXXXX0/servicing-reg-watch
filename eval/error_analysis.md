# Eval error analysis

Written after scoring (`eval/results.md`, commit a0abaa6), using `eval/sample_manifest.csv`,
the committed triage outputs, the Stage B log and the saved GovInfo full text. Triage and
`pipeline/triage_prompt.md` were not changed or re-run.

Two model errors in 30 labeled documents: 1 false negative, 1 false positive. The
prefilter kept both (manifest: `keep`, `A_cfr_part`; reproduced by `prefilter.classify`),
so cause (a) does not apply to either.

Root-cause codes: (a) prefilter drop; (b) gap in the relevance test in
`pipeline/triage_prompt.md`; (c) document-structure handling; (d) scope misapplied in
triage; (e) genuinely borderline.

## False negatives

### 2025-22490: NCUA, Guidance on Response Programs for Unauthorized Access to Member Information (label Y, DATA.PRIVACY_SECURITY)

- Manifest: drawn by the unfiltered query; prefilter `keep` (`A_cfr_part`, 12 CFR 748).
- Triage: Stage A said relevant (0.6, rows BANKSEC-GUIDE-001 and NCUA-CYBER-001). Stage B read
  1,500 of 2,179 words and reversed it to not relevant (0.75): "no substantive compliance
  obligation changes."
- The document: a proposed rule to remove Appendix B from 12 CFR 748 and republish the same
  content as a Letter to Credit Unions. It says three times that it makes no substantive
  change. The unread 679 words repeat that, so the partial read did not cause the miss.
- **Root cause: (b), gap in the relevance test.** The test covers guidance that is
  *withdrawn* ("Withdrawing guidance is a change under this test"). It says nothing about
  guidance being *removed from the CFR and reissued in another form*. That change affects
  how the guidance is recognized and how it can be amended later (no notice and comment),
  even though its content stays the same. Without a rule, Stage B fell back on the
  document's own "no substantive change" statement. Close to (e): a reviewer could
  reasonably call this not relevant. The FR type label ("Proposed Rule") and the ACTION
  line agree, so (c) does not apply.

## False positives

### 2024-22962: CFPB, Debt Collection Practices (Regulation F); Deceptive and Unfair Collection of Medical Debt (label N)

- Manifest: drawn by the "Regulation F" query; prefilter `keep` (`A_cfr_part`, 12 CFR 1006).
- Triage: relevant at both stages (Stage A 0.55, Stage B 0.7; Stage B read 4,000 of 11,228
  words). Rows REGF-FEES-001 and UDAAP-001; classes PAYMENT.FEES, NEGOTIATION.TREATMENT,
  DISCLOSURE.REQUIRED. The rationale says the part III.A reading of 1006.18(b)(2)(i) and
  1006.22(b) "is not specific to medical debt."
- The document: an advisory opinion (FR type label says "Rule"; the ACTION line says
  "Advisory opinion"). Triage recorded `change_type: guidance`, so it read the ACTION line
  correctly and (c) does not apply. The SUMMARY says it is issued "to remind debt
  collectors" of existing FDCPA and Regulation F prohibitions for medical debt. Part III.A
  restates FDCPA 808(1) and 807, then applies them to medical billing and insurer
  adjustments. The CFPB withdrew it in 2025-08286.
- **Root cause: (b), gap in the relevance test.** As written, the prompt supports the
  model's answer. Advisory opinions "count as clarifying an obligation when they interpret
  how an obligation within the test applies." A Regulation F provision governs every
  collector. "A document in one of these areas is relevant if some part of it meets the
  test." The test does not say that guidance aimed at a non-loan debt type (medical,
  rent, utilities), or one that only restates existing law for that debt type, is out of
  scope, and medical debt is not on the "Not relevant unless" list. You could argue (d)
  (scope misapplied) instead, but triage applied the text it was given, so the fix belongs
  in the prompt.

## Note on Stage A vs Stage B for the eval sample

Stage A answers (`data/triage_stage_a/`) would have produced the same counts: TP 5, FP 1
(2024-22962), FN 1 (2024-30824), TN 23. Stage B fixed 2024-30824 (not relevant to relevant)
and introduced the 2025-22490 miss (relevant to not relevant). With one error each way,
this sample cannot show that Stage B improves relevance calls. It does show that Stage B
flips relevance, and that each flip changes the outcome.
