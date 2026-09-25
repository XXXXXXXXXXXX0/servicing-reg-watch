# Status

Branch: `claude/eloquent-goodall-jas2zw` (no PR opened).

## Completed
- Full text (GovInfo) and eCFR diffs for 215 docs (201 prefilter survivors + 14 dropped eval docs).
- Triage in-session: Stage A on 215, Stage B full-text reads on 35; 22 relevant, 22 change records.
- Final blind labels in `eval/labels.csv`: 6 relevant, 24 not relevant; tiers not supplied.
- Scored v1 triage unchanged (`eval/results.md`): TP 5, FP 1, FN 1, TN 23. Precision 5/6, recall 5/6,
  specificity 23/24, prefilter recall 6/6, end-to-end recall 5/6; behavior-class exact match 2/5.
- Error analysis (`eval/error_analysis.md`): FN 2025-22490 and FP 2024-22962, both (b) relevance-test gaps.

## Data files (committed)
- `data/raw/` store (FR metadata, GovInfo htm, eCFR), `data/triage/` (+ `_stage_b.jsonl`), `data/triage_stage_a/`.

## Open issues
- Prompt gaps from the eval: guidance removed from the CFR but reissued elsewhere; guidance aimed at a
  non-loan debt type (e.g. medical) that restates general collector law. Triage prompt unchanged so far.
- At n=6 positives, rates have wide intervals (5/6: 35.9% to 99.6%).
- route.py sends every relevant doc to review; the < 0.7 flag is in the triage confidence only.
- Register gaps raised in records: FCRA permissible purpose; FCRA medical info (1022.30); NCUA
  indirect-vehicle servicer rule; state credit reporting.

## Next step
- Await Angela's decision on the two prompt gaps before changing `pipeline/triage_prompt.md` or re-running triage.
