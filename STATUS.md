# Status

Branch: `claude/eloquent-goodall-jas2zw` (no PR opened).

## Completed
- GovInfo full-text source (API granule /htm with header key; www fallback), cached per document.
- CLAUDE.md standing rules; relevance test in `pipeline/triage_prompt.md`.
- Prefilter: exclude administrative notices, keep on A (CFR part), B (CFPB type), C (keyword); rules in PREFILTER.md. No CFR inference; 12 CFR 53/304/1090 restored.
- Live FR ingest committed as a compressed store; fetches read the store first.

## Data files (committed)
- `data/raw/federal_register.jsonl.gz`: 2,203 documents, 2024-09-23..2026-09-24, 560 KB.
- `data/raw/ingest_manifest.json`: per agency-month counts, 75 KB.
- No full text, eCFR text or diffs fetched yet.

## Open issues
- Prefilter not yet applied to the full set; eval manifest not yet updated from real metadata.
- CI live job needs a `GOVINFO_API_KEY` repository secret.
- Triage not run.

## Next step
- Apply the prefilter to the full ingested set; update `eval/sample_manifest.csv`.
