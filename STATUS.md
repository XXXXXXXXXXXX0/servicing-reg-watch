# Status

Branch: `claude/eloquent-goodall-jas2zw` (no PR opened).

## Completed
- v1 eval final (`eval/results.md`): TP 5, FP 1, FN 1, TN 23. Labels, scores and all 215 triage outputs unchanged.
- v1.1 (derived from v1 eval errors; untested on a fresh set), `pipeline/triage_prompt.md`: legal-status, non-loan debt, ACTION-line and who-it-binds rules; `interpretation` type (control validation); primary/secondary classes (v1 outputs still validate).
- `eval/v1_1_fixes.md` records the errors, root causes, fixes and gap check. `eval/v1_1_conflicts.md` lists 5 relevance and 4 change-type conflicts.
- Records (`records/record_meta.yaml`; `python -m pipeline.records annotate` / `check`): supersession links (7 closed), `interpretation` on 7, primary/secondary split on all 24.
- Human review (`records/REVIEW_LOG.md`): records created for 2025-22490 and 2025-22489 (interpretation, open); 2024-22962, 2024-27791 and 2024-29292 closed as not relevant.
- Register: 4 gap rows (3 `verify` cited to committed FR text, 1 `unresearched` state row); 73 rows.

## Data files (committed)
- `data/raw/` store, `data/triage/` (+ `_stage_b.jsonl`), `data/triage_stage_a/`: unchanged this session.

## Open issues
- v1.1 rules are untested: a fresh labeled eval set is needed to measure them.
- New register rows are not yet linked from the records that raised them. Their statute and eCFR text has not been read.

## Watch list
- 2024-29292 (CFPB Reg V ANPR, identity theft and coerced debt): signals future identity-theft block obligations under Regulation V; closed as not relevant (no proposed text).

## Next step
- Draw and label a fresh eval set to test v1.1; sign off control validation on 2025-22490 and 2025-22489.
