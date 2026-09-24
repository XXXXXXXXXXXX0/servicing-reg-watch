# Status

Branch: `claude/eloquent-goodall-jas2zw` (no PR opened).

## Completed
- GovInfo full-text source (API granule /htm, key in header; www fallback); saved as `.htm.gz`.
- CLAUDE.md rules (END OF PROMPT, STATUS handoff, committed-store cache); relevance test plus supervisory/enforcement/advisory-opinion clause in `pipeline/triage_prompt.md`.
- Prefilter (PREFILTER.md): exclude administrative notices, keep on A/B/C. No CFR inference; 12 CFR 53/304/1090 restored.
- Live FR ingest committed; fetches read `data/raw/` first (closed months, text, eCFR text, eval searches).
- Prefilter run on full set: 2,203 docs -> 201 kept (A 102, B 35, C 64), 1,052 excluded, 950 no_match.
- `eval/sample_manifest.csv` recomputed from real metadata: 16 keep, 14 drop.

## Data files (committed)
- `data/raw/federal_register.jsonl.gz`: 2,203 docs, 2024-09-23..2026-09-24 (~0.55 MB).
- `data/raw/ingest_manifest.json`: 175 agency-months, all complete (~43 KB).
- Not yet fetched: GovInfo full text, eCFR text, diffs. Prefilter output is runtime (`data/prefilter/`, ignored).

## Open issues
- CI live job needs a `GOVINFO_API_KEY` repository secret; CI does not commit store files.
- eCFR versions index is always queried (not cached by design).
- Triage not run; eval labels still blank.

## Next step
- Fetch GovInfo full text for the 201 kept documents (`python -m pipeline.ingest text`), commit `data/raw/govinfo/`, then diff and triage.
