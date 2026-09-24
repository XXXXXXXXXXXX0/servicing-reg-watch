# Status

Branch: `claude/eloquent-goodall-jas2zw` (no PR opened).

## Completed
- Full text: GovInfo API for prefilter survivors + eval sample (215 docs, `--include-eval`): 215 fetched, 0 failed, 6.4 MB gz.
- eCFR diffs for the same 215: 22 diffed, 32 proposed, 9 no matching version, 8 no effective date, 1 pending.
- Triage in-session (no API). Stage A (abstract, metadata, diff excerpt): 215, all valid; 22 relevant.
- Stage B (full text, <= ~4,000 words) on 35 docs: relevance changed for 4 (2 to relevant, 2 to not relevant); 12 more changed other fields.
- Final: 22 relevant; route: 47 review (22 relevant, 25 not relevant < 0.85), 168 auto-closed; 22 change records in `records/`.
- Human-review flags: 0 for missing full text; 2 with confidence < 0.7 after Stage B (2024-30824 and its correction).
- Stage B log: `data/triage/_stage_b.jsonl`; `eval/run_eval.py` now renders a Stage A/B summary in `eval/results.md`.

## Data files (committed)
- `data/raw/govinfo/*.htm.gz` (215), `data/raw/ecfr/*.gz` (104, 7.2 MB), plus the FR store and manifest.
- `data/triage/` (final answers + `_stage_b.jsonl`), `data/triage_stage_a/` (Stage A answers); gitignore and CLAUDE.md updated.

## Open issues
- Blind labeling: eval-candidate triage now sits in `data/triage*/`, `records/`, `records/REVIEW_QUEUE.md`. Label before opening them.
- route.py sends every relevant doc to review; the < 0.7 flag is in the triage confidence, not a separate queue.
- Register gaps raised in records: FCRA user permissible purpose; FCRA medical info (1022.30); NCUA indirect-vehicle servicer rule; state credit reporting.
- Stage B read partial text for long documents (words read per doc in the log). TPRM-001 cite 88 FR 37920 seen in 2026-18859; row still `verify`.

## Next step
- Blind-label `eval/labels.csv`, then `python eval/run_eval.py`; reviewers sign off records; research the register gaps.
