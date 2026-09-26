# Status

Branch: `claude/eloquent-goodall-jas2zw` (no PR opened).

## Completed
- v1 eval final (`eval/results.md`): TP 5, FP 1, FN 1, TN 23. Labels, scores and all 215 triage outputs unchanged.
- v1.1 (derived from v1 eval errors; not yet tested on a fresh eval set). `pipeline/triage_prompt.md`:
  - rules for legal-status changes, non-loan debt guidance, ACTION line over FR type label, who the document binds;
  - `interpretation` change type (control validation);
  - primary and secondary behavior classes (schema v1.1; v1 outputs still validate).
- `eval/v1_1_fixes.md` records the errors, root causes, fixes and gap check. `eval/v1_1_conflicts.md` lists 5 relevance and 4 change-type conflicts.
- Records: `records/record_meta.yaml`, applied by `python -m pipeline.records annotate`, validated by `check`:
  - supersession links (7 records closed);
  - `interpretation` on 7 records;
  - primary/secondary split on all 23.
- Human review (`records/REVIEW_LOG.md`): 2025-22490 record created (interpretation, open); 2024-22962 closed as not relevant.
- Register: 4 gap rows (3 `verify` cited to committed FR text, 1 `unresearched` state row); 73 rows.

## Data files (committed)
- `data/raw/` store, `data/triage/` (+ `_stage_b.jsonl`), `data/triage_stage_a/`: unchanged this session.

## Open issues
- v1.1 rules are untested: a fresh labeled eval set is needed to measure them.
- 2025-22489 (NCUA Appendix A, same legal-status change as #12) is unreviewed. 2024-27791 and 2024-29292 conflict with v1.1 and await review.
- New register rows are not yet linked from the records that raised them. Their statute and eCFR text has not been read.

## Next step
- Review the three pending v1.1 conflicts; draw and label a fresh eval set to test v1.1.
