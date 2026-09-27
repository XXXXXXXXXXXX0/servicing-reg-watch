# Status

Branch: `claude/eloquent-goodall-jas2zw`. v1.2 scope expansion in progress (plan approved; steps 1-7).

## Completed
- v1 eval final (`eval/results.md`): TP 5, FP 1, FN 1, TN 23. Unchanged by v1.2.
- v1.1 rules (untested on a fresh set); human review: 5 overrides (`records/REVIEW_LOG.md`).
- v1.2 step 1: `taxonomy/product_lines.yaml` (6 lines, every class mapped; PAYMENT.* includes recovery).
- v1.2 step 2: `taxonomy/segments.yaml`; 73 rows mapped (INVENTORY.md). 17 FDCPA rows unclear for all segments; state rows unclear for bank/credit_union (preemption unresearched).

## Data files (committed)
- `data/raw/` store, `data/triage/`, `data/triage_stage_a/`: unchanged so far.

## Open issues
- v1.1 rules untested; no register row verified (VERIFY_CHECKLIST.md).
- 44 of 47 review-queue documents open for the operating team.

## Watch list
- 2024-29292 (Reg V ANPR, coerced debt); 2026-07960 (FCC onshoring NPRM).

## Next step
- v1.2 step 3: product lines, segments, priority on records; indexes; queue sort.
