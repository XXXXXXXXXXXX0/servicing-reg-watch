# Status

Branch: `claude/eloquent-goodall-jas2zw` (PR into main opened this session).

## Completed
- v1 eval final (`eval/results.md`): TP 5, FP 1, FN 1, TN 23. Labels, scores and all 215 triage outputs unchanged.
- v1.1 (untested on a fresh set): legal-status, non-loan debt, ACTION-line and who-it-binds rules; `interpretation` type; primary/secondary classes. Fixes in `eval/v1_1_fixes.md`; conflicts in `eval/v1_1_conflicts.md`.
- Human review (`records/REVIEW_LOG.md`): 5 overrides (2 records created as interpretation, 3 closed as not relevant).
- README.md rewritten as the Section 12 memo, every number sourced from eval/ and records/.
- VERIFY_CHECKLIST.md: all 69 `status: verify` register rows with citation and source URL (4 unresearched rows excluded).

## Data files (committed)
- `data/raw/` store, `data/triage/` (+ `_stage_b.jsonl`), `data/triage_stage_a/`: unchanged this session.

## Open issues
- v1.1 rules are untested: a fresh labeled eval set is needed.
- No register row is verified; work VERIFY_CHECKLIST.md. New gap rows are not yet linked from the records that raised them.
- 44 of 47 review-queue documents remain open for the operating team (incl. 2025-22490, 2025-22489 awaiting control validation); 3 closed by review.

## Watch list
- 2024-29292 (CFPB Reg V ANPR, coerced debt): future identity-theft block obligations.
- 2026-07960 (FCC onshoring NPRM): asks whether to extend to all foreign-originated TCPA 227(c)/(d) calls.

## Next step
- Draw and label a fresh eval set to test v1.1; verify register rows.
