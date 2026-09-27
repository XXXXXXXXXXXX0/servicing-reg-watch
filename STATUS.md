# Status

Branch: `claude/eloquent-goodall-jas2zw`. v1.2 scope expansion in progress (plan approved; steps 1-7).

## Completed
- v1 eval final (TP 5, FP 1, FN 1, TN 23; unchanged by v1.2); v1.1 rules; 5 human review overrides.
- v1.2 step 1: `taxonomy/product_lines.yaml` (6 lines, every class mapped; PAYMENT.* includes recovery).
- v1.2 step 2: `taxonomy/segments.yaml`; 73 rows mapped (INVENTORY.md). 17 rows unclear for all segments (11 Reg F, TX-TDCA-002, 5 vendor-side or AI-law rows); state rows unclear for bank/credit_union (preemption unresearched).
- v1.2 step 3: `v1_2_scope` on all 24 records (record_meta.yaml; 21 unsigned record files); BY_PRODUCT_LINE.md, BY_SEGMENT.md; queue sorted by priority, then line. 3 signed records left untouched: changing a signed record, even with metadata, is a post-approval change.
- v1.2 step 4: 18 register rows (15 verify, citations confirmed from eCFR 2026-09-24 / GovInfo text; 3 unresearched: CARDNET-CHARGEBACK-001, STATE-PAYOFF-001, STATE-TOTALLOSS-001); classes DISPUTES.ERROR_RESOLUTION, DISPUTES.CLAIMS_DEFENSES, RECORDS.RETENTION; rule A +7 parts, rule C +16 keywords; DoD ingested (1,481 docs), kept only on 32 CFR 232 / MLA keywords: 0 kept.
- v1.2 step 5: triage_prompt.md v1.2 section (disputes/chargebacks, Holder Rule, record retention, payoff/title release; deposit exclusion narrowed). eval/v1_2_conflicts.md: 3 relevance conflicts (2024-29699 eval doc, auto-closed; 2025-00565; 2025-08646), 1 class conflict (2024-30758). v1 outputs and eval unchanged.

## Data files (committed)
- `data/raw/federal_register.jsonl.gz` (3,683 docs, +DoD), `ingest_manifest.json`, 14 new `data/raw/ecfr/2026-09-24_*.gz`. `data/triage*`: unchanged so far.

## Open issues
- v1.1 rules untested; no register row verified (VERIFY_CHECKLIST.md).
- 44 of 47 review-queue documents open. Watch: 2024-29292 (Reg V ANPR), 2026-07960 (FCC onshoring NPRM).

## Next step
- v1.2 step 6: coverage check for product lines and segments; thin areas.
