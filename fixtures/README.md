# Fixtures (synthetic)

Everything in this directory is a **synthetic test fixture**. None of it is a real
Federal Register document, real eCFR text, or real triage of a real document.
Document numbers use the `FIXTURE-NNNN` form and URLs point at `example.invalid`
so they cannot be mistaken for real records.

- `federal_register/documents.json`: documents shaped like Federal Register API
  `documents.json` results. `sources.FixtureClient` filters and pages them the way
  the API does (agency, type, publication-date window, `per_page`/`page`).
  `window.json` is the fixed window and "today" used for offline runs.
- `ecfr/`: eCFR versioner responses. `versions-title-{T}-part-{P}.json` answers
  `/versions/title-{T}.json?part={P}`, and `full-{date}-title-{T}-section-{S}.xml`
  answers `/full/{date}/title-{T}.xml?section={S}`. The section text is invented;
  it is not the CFR.
- `text/`: full-text bodies for a few documents (the `raw_text_url` target). Kept
  documents without a body exercise the `full_text_unavailable` route to review.
- `triage/`: hand-written triage outputs for some fixture documents, used to test
  validation, routing, records and the eval script. They cover a relevant final rule
  with an eCFR diff, a guidance withdrawal, a pending-effective rule, a
  high-confidence hard negative (auto-closed), a proposed rule, and two
  low-confidence negatives. The remaining kept fixtures stay untriaged so the
  "untriaged goes to review" path is exercised.

The fixture set is designed to exercise each prefilter decision (tracked CFR
part, domain terms, CFPB rulemaking, withdrawal, noise, no signal), each diff
status, multi-agency de-duplication, and window filtering.
