# Details behind the README memo

Detail moved out of [`README.md`](../README.md). Sections marked **(v1.1)** give counts as of
the v1.1 run (2,203 documents, seven agencies); the v1.2 counts are in the README,
[`PREFILTER.md`](../PREFILTER.md) and [`STATUS.md`](../STATUS.md). Links are relative to this
folder.

## Problem

AI agents that service US consumer loans call and text borrowers, take payments, and handle
disputes, insurance claims and recovery. Each of those behaviors is governed by rules that
change. The rules come from the CFPB, FCC, FTC, the bank and credit union regulators, the
states and Nacha. Changes arrive as final rules, proposals, delays, guidance and, just as
important, **withdrawals and rescissions of guidance**. A deploying team needs three things:
to learn about a change quickly, to know which agent behaviors it touches, and to leave an
audit trail showing that a human decided what to do about it.

## First human review overrides (2026-09-26)

All later decisions are in [`records/REVIEW_LOG.md`](../records/REVIEW_LOG.md).

| Document | Model (v1) | Reviewer decision |
|---|---|---|
| 2025-22490, NCUA breach-response guidance (eval #12) | Not relevant, 0.75 | Relevant; record created, `interpretation` (open, awaits control-validation sign-off) |
| 2025-22489, NCUA safeguarding guidelines | Not relevant, 0.75 | Relevant; record created, `interpretation` (open, awaits control-validation sign-off) |
| 2024-22962, CFPB medical-debt advisory opinion (eval #25) | Relevant, 0.70 | Not relevant; record closed |
| 2024-27791, applicability-date revision of 2024-22962 | Relevant, 0.70 | Not relevant; record closed to match 2024-22962 |
| 2024-29292, CFPB Regulation V ANPR on identity theft and coerced debt | Relevant, 0.75 | Not relevant; record closed; on the watch list |

## Sources and data (v1.1)

- **Ingest.** Federal Register API, 7 agencies, rules, proposed rules and notices,
  2024-09-23 to 2026-09-24: 2,203 documents. Queries run per agency and month;
  `data/raw/ingest_manifest.json` records reported and retrieved counts for every chunk, so
  completeness is checkable.
- **Prefilter** ([`PREFILTER.md`](../PREFILTER.md)). The original spec only asked for a "cheap
  keyword/CFR-part filter to drop obvious noise" and defined no criteria. The rules were
  designed from the register and the behavior taxonomy:
  - **Exclusion first.** Administrative notices (Paperwork Reduction Act collections,
    Sunshine Act meetings, Privacy Act system-of-records notices, agency organization, FCC
    spectrum/broadcast/licensing) are dropped before any keep rule: 1,052 documents.
  - **Then keep on any of three rules:** a tracked CFR part in the document's own metadata
    (A), a CFPB rule or guidance document or guidance withdrawal (B), or a register keyword
    in the title or abstract (C). 201 kept (A 102, B 35, C 64); 950 dropped as `no_match`.
  - **Biased toward keeping.** The CFR part list is a floor: parts are added freely and
    removed only with a stated reason. Hard negatives such as mortgage servicing pass on
    purpose; separating them is triage's job. A coverage check (enforced by a test) confirms
    every register row and behavior class (and, since v1.2, every product line and segment)
    is reachable by some rule.
  - Every drop is logged with its reason code to `data/prefilter/dropped.jsonl`.
- **Full text from GovInfo.** Federal Register full-text pages redirect to a bot wall
  (`unblock.federalregister.gov`) from this environment, so full text comes from the GovInfo
  API granule endpoint (key in the `X-Api-Key` header), with the public GovInfo content link
  as fallback. All 215 documents were fetched; 0 missing.
- **Cached in the repo.** Fetched data is committed as compressed files under `data/raw/`
  (`federal_register.jsonl.gz`, `govinfo/*.htm.gz`, `ecfr/*.gz`, `fr_search/*.json.gz`).
  Every fetch function checks the store first and never refetches what is saved.
- **Diff coverage.** Of the **72** triaged documents that cite a tracked CFR part:
  - **22** were diffed against eCFR point-in-time text (the day before vs. the effective date);
  - **32** are proposed rules, with no codified change to diff yet;
  - **18** were triaged without a diff: 9 had no matching eCFR version on their effective
    date, 8 had no effective date in the Federal Register metadata (the pipeline does not
    guess one), and 1 had a future effective date, so eCFR had no after-text yet.
- **Long documents are partially read.** Stage B reads at most about 4,000 words of full
  text. 26 of the 35 Stage B reads were partial. Words read and total words are logged per
  document in `data/triage/_stage_b.jsonl` and stated in each record's Triage section.
- **Engineering rules** ([`CLAUDE.md`](../CLAUDE.md)): repo-committed caching, no refetching of
  saved data, no secrets in the repo, logs, URLs or error messages, and no invented
  citations.

## What testing caught

- **A silent failure that only live data showed.** The offline fixtures had only section
  versions, so the diff step handled only eCFR *section* versions and passed every test. On
  the live eCFR API, rules that amend an *appendix*, including the **Official
  Interpretations** (for example, Supplement I to Part 1026, which carries most annual
  threshold adjustments), were skipped with no error: those documents simply came back as
  having no diff. After the fix (fetch appendix versions with the `appendix=` parameter),
  diffed documents went from **12 to 22**. The same live run found that eCFR `/full` returns
  406 without a compressed `Accept-Encoding`, and that Federal Register text URLs hit a bot
  wall.
- **Register gaps the pipeline surfaced on its own.** Change records raised obligations the
  register did not hold. Four rows were added in v1.1: FCRA-PERMPURP-001 (permissible
  purpose), FCRA-MEDINFO-001 (creditor medical-information prohibition), NCUA-INDIRECT-001
  (removal of NCUA indirect-vehicle third-party servicer limits) and STATE-CREDITRPT-001
  (state credit reporting laws, `unresearched`). Their current verification status is in
  [`register/VERIFICATION_REPORT.md`](../register/VERIFICATION_REPORT.md).

## Design choices

- **Each document is judged as published.** A later withdrawal, disapproval or vacatur does
  not rewrite the earlier triage. It is linked instead: records carry `supersedes` and
  `superseded_by` (in `records/record_meta.yaml`), and a withdrawal, final rule, disapproval
  or vacatur closes or reverses the earlier record, while an amendment or correction leaves
  it open. For example, 2025-08286 closes 2024-22962 and
  2024-27791.
- **Interpretations route to control validation, not behavior change.** Supervisory findings,
  interpretive rules, restating guidance and legal-status changes get change type
  `interpretation`: the required action is to check existing controls against the stated
  reading, not to change agent behavior. Supervisory Highlights Issue 37 is the model case: it
  states no new rule, but it says how examiners read FCRA dispute duties, so the controls
  should be checked against it. The CFPB guidance withdrawal (2025-08286) is the reverse case:
  it changes the legal status of guidance without changing the statute, so controls are
  re-validated against their statutory source rather than removed.
- **Behavior classes, not workflows.** Impact maps to a public reference taxonomy
  (`taxonomy/behaviors.yaml`, 20 classes since v1.2). The pipeline never names or guesses at a vendor's
  internal agents, scripts or configs.
- **Fail toward human review.** Only confident "not relevant" calls are auto-closed.
- **Diffs come from eCFR, not the rule preamble**, and the diff step reports
  `pending_effective`, `effective_date_unknown` or `no_matching_ecfr_version` rather than
  guessing a date.
- **One triage contract, two modes.** `pipeline/triage_prompt.md` is the only statement of the
  triage instructions, for API mode and in-session mode alike. Both pass the same validator
  (JSON Schema plus semantic checks); invalid API output goes to `data/triage/_rejected/`,
  never the queue.
- **Records are append-safe.** A record whose `Reviewer:` line is filled in is never
  overwritten by a later run.

## Provenance method

Each register row records **why it is in the register**: `salient_stated` (named on
Salient's public pages), `third_party_stated` (named in a third-party description of
Salient), or `added_by_analysis` (added because the regulations reach a modeled behavior).
`provenance_url` is null wherever the page was not captured. Every row's `source_url` points
at primary text where one is public (eCFR, uscode.house.gov, state legislature sites, FCC
documents); for licensed rulebooks such as Nacha and PCI DSS, it points at the publisher's
page.

## How the adapter plugs into a real deployment

`adapter/deployment_map.template.yaml` lists every behavior class with blank
`owning_system`, `config_ref`, `test_suite_ref` and `approver_role`. A deploying team copies
it into its own repository and fills it in. Each change record names the affected behavior
classes and asks four standard questions: owning config or script, approver, rollout
sequence and test evidence. The filled map answers the first two directly and points at the
evidence for the fourth. Nothing in this repository reads the filled map yet; the next step
is a small consumer that pre-fills those answers in each record.

