# Status

Branch: `claude/eloquent-goodall-jas2zw`. v1.2 scope expansion complete (steps 1-7).

## Completed
- v1 eval final (TP 5, FP 1, FN 1, TN 23; unchanged by v1.2); v1.1 rules; 5 human review overrides.
- v1.2 1-2: `taxonomy/product_lines.yaml` (6 lines; priority rule incl. DISPUTES.ERROR_RESOLUTION), `taxonomy/segments.yaml` (91 rows mapped; unclear where not settled).
- v1.2 3: `v1_2_scope` for all records; BY_PRODUCT_LINE.md, BY_SEGMENT.md; queue sorted. 3 signed records untouched: editing a signed record, even metadata, is a post-approval change.
- v1.2 4: 18 rows (15 verify, eCFR/GovInfo-confirmed; 3 unresearched); 3 classes; rule A +7 parts, rule C +16 keywords; DoD ingested, kept only on 32 CFR 232 / MLA keywords.
- v1.2 5: prompt v1.2 section; `eval/v1_2_conflicts.md` (3 relevance, 1 class conflict).
- v1.2 6: coverage test covers lines and segments; thin: insurance_claims, bank/CU (many unclear), captive/specialty (no row binds either alone).
- v1.2 7: prefilter 206 kept of 3,683; 5 new (FDIC 2, NCUA 3), 0 DoD. Triage: 0 relevant; 2 NCUA (Stage B, 0.75) to review, 3 auto-closed. Queue 49 open, 171 closed.

## Data files (committed)
- Store: `federal_register.jsonl.gz` (3,683 docs), manifest, 14 new eCFR, 5 new GovInfo files.
- `data/triage/` (+5, `_v1_2_docs.json` excluded from v1 eval counts), `data/triage_stage_a/` (+5).

## Open issues
- 2024-29699 (auto-closed, eval doc) conflicts under v1.2; confirm it is still in force before reopening.
- No register row verified; VERIFY_CHECKLIST.md now lists 84 rows. v1.1 and v1.2 rules untested on a fresh set.
- Watch: 2024-29292 (Reg V ANPR), 2026-07960 (FCC onshoring NPRM).

## Next step
- Human review of v1_2_conflicts.md and the 2 NCUA items; state research for thin areas; fresh eval set.
