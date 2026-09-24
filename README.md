# servicing-reg-watch

**Memo: Regulatory change management for AI loan-servicing agents (v1)**

Built without access to any production system. Not legal advice.

## Problem

AI agents that service US consumer loans call and text borrowers, take payments,
and handle disputes, insurance claims and recovery. Each of those behaviors is
governed by rules that change. Rules come from the CFPB, FCC, FTC, the bank and
credit union regulators, the states, and Nacha. Changes arrive as final rules,
proposals, delays, guidance, and, just as important, **withdrawals and rescissions
of guidance**. A deploying team needs three things: to learn about a change quickly,
to know which agent behaviors it touches, and to leave an audit trail showing that
a human decided what to do about it.

## What v1 does

```
Federal Register API ──► 1 ingest ──► 2 prefilter ──► 3 eCFR diff ──► 4 triage ──► 5 route ──► 6 change records
 (7 agencies, 24 mo,       raw JSON     keyword/CFR    section-level    JSON that    auto-close   one .md per
  RULE/PRORULE/NOTICE)     + abstract   filter; every  before/after     validates    only if      relevant doc,
                                        drop logged    text             vs schema    not relevant with reviewer
                                                                                     & conf≥0.85  sign-off
```

| Path | What it is |
|---|---|
| `register/federal.yaml`, `register/states/*.yaml` | Register rows (BUILD_SPEC §4 schema). Each row cites a primary source. |
| `register/INVENTORY.md` | Generated from the YAML: `python -m pipeline.inventory` (`--check` in CI). |
| `register/research_backlog.yaml` | State × topic gaps that have no primary citation yet, so they are not rows. |
| `taxonomy/behaviors.yaml` | 17 behavior classes (reference model) and the `applies_to` vocabulary. |
| `pipeline/` | `ingest`, `prefilter`, `diff`, `triage`, `route`, `records`, `inventory`, `run` |
| `pipeline/triage_prompt.md` | Triage instructions, shared by API mode and in-session mode. |
| `pipeline/triage_schema.json` | JSON Schema for triage output (BUILD_SPEC §7 step 4). |
| `adapter/deployment_map.template.yaml` | Empty deployment adapter interface (§9). |
| `fixtures/` | **Synthetic** API responses and triage outputs for offline tests. |
| `eval/` | `select_sample.py`, `labels.csv`, `run_eval.py`, `results.md`. |
| `records/` | Generated change records. |

### Quick start

```bash
pip install -r requirements.txt                 # + requirements-api.txt for API triage
python -m pytest -q                             # offline; sockets are blocked in tests
python -m pipeline.run --offline --with-fixture-triage --data-dir /tmp/srw/data --records-dir /tmp/srw/records

python -m pipeline.run                          # live: ingest → prefilter → text → diff → triage inputs → route → records
python -m pipeline.triage status                # packets awaiting triage
python -m pipeline.triage validate              # check triage JSON against the schema and register
```

## Design decisions

- **Behavior classes, not workflows.** Impact maps to a public reference taxonomy
  (`CONTACT.FREQUENCY`, `STOP.TRIGGERS`, …). The pipeline never names or guesses at
  a vendor's internal agents, scripts or configs. The adapter is where a deployment
  connects classes to its own systems.
- **Chunked, verifiable ingest.** Queries run per agency and per month. A chunk
  larger than the API will page through is split in half until it fits.
  `data/raw/ingest_manifest.json` records reported and retrieved counts for every
  chunk, and ingest exits non-zero if any chunk comes back short. That makes
  "ingested all listed agencies for the window" checkable rather than asserted.
  Multi-agency documents are stored once.
- **The prefilter is a stated rule set, not a tuned score.** Administrative notices
  (paperwork, Sunshine Act, Privacy Act system-of-records, agency organization,
  FCC spectrum/broadcast/licensing) are excluded first. Then a document is kept if
  it cites a tracked CFR part (A), is a CFPB rule or guidance document (B), or has
  a listed keyword in its title or abstract (C); everything else is dropped. Rules
  and reasons are in [PREFILTER.md](PREFILTER.md). Every drop is written with its
  reason to `data/prefilter/dropped.jsonl`. Hard negatives such as mortgage
  servicing deliberately pass the prefilter; separating them is triage's job.
- **Diffs come from eCFR, not the rule preamble.** For final rules on a tracked part,
  the diff step finds the eCFR section versions dated on the rule's effective date
  and diffs the section text from the day before against the effective date. It
  reports `pending_effective`, `effective_date_unknown` or `no_matching_ecfr_version`
  rather than guessing a date.
- **Two triage modes, one contract.** `triage_prompt.md` is the only statement of the
  triage instructions. API mode (`python -m pipeline.triage api`; `MODEL` env,
  default `claude-sonnet-5`; `ANTHROPIC_API_KEY`) sends it, with the register, taxonomy
  and schema, as a cached system prompt and requests schema-constrained JSON. In
  in-session mode, an operator writes `data/triage/<doc_id>.json` by hand from the
  same prompt. Both modes pass the same validator: the JSON Schema plus semantic
  checks. Register IDs must exist, a relevant document needs at least one behavior
  class, and `doc_id` must match its packet. API output that fails validation goes
  to `data/triage/_rejected/` and never into the queue.
- **Fail toward human review.** Routing auto-closes only when `relevant=false` **and**
  `confidence ≥ 0.85`. A document that is untriaged or has invalid output lands in
  the review queue, never in auto-closed.
- **No triage from partial information.** Triage needs the document's full text.
  When it cannot be fetched, the document is not triaged; it goes to human review
  with route reason `full_text_unavailable`, and the reason the text is missing is
  logged in `data/raw/text/_missing.json` and shown in the review queue. Full text
  comes from GovInfo, not federalregister.gov (whose text URLs redirect to a bot
  wall): first the API granule endpoint
  (`api.govinfo.gov/packages/FR-<date>/granules/<doc>/htm`, key from
  `GOVINFO_API_KEY` sent in the `X-Api-Key` header), then the public
  `www.govinfo.gov/content/pkg/FR-<date>/html/<doc>.htm` link as fallback. Every
  response is saved as fetched to `data/raw/govinfo/<doc>.htm.gz` (committed) and
  never fetched again; the tag-stripped text goes to `data/raw/text/` (runtime).
- **Fetched data is committed, compressed, and never refetched.** Federal Register
  metadata lives in `data/raw/federal_register.jsonl.gz`; ingest serves any
  agency-month that was fetched completely after it ended from that file and
  queries only open or new months. GovInfo text, eCFR point-in-time section text
  and eval term searches are saved the same way. The eCFR versions index is always
  queried, because it gains entries when rules are amended. Each committed file
  must stay under 50 MB. Everything else under `data/` is gitignored runtime output.
- **Records are append-safe.** A change record whose `Reviewer:` line has been filled
  in is never overwritten by a later run.

## What is deliberately not automated, and why

- **Approval.** AI narrows the queue; humans decide. No record is marked done, and
  no register row is changed, by the pipeline.
- **Unresearched coverage.** Rows with `status: unresearched` (the four
  multi-state INSURANCE.CLAIMS topics) record a known gap. They carry
  `citation: null`; the validator rejects a citation on them, so none can be
  filled in without research. INVENTORY.md lists them under "Coverage map: state
  research pending".
- **Register verification.** Every researched row ships as `status: verify` with
  `last_checked: null`. The rows were drafted from working knowledge of the law
  without the primary text open. Flipping a row to `verified` requires a person to
  read the primary source, and the validator rejects `verified` without
  `last_checked`.
- **Mapping to a deployment.** The adapter ships empty. Only the deploying team knows
  which config or script implements a behavior, and a guessed mapping would be worse
  than none.
- **State law and Nacha monitoring.** There is no Federal Register feed for these.
  They are `change_source: manual` rows and need a person watching them.

## Eval results

**None yet.** `eval/results.md` is generated from `eval/labels.csv`, which currently
has no rows. The protocol (BUILD_SPEC §10) is ready to run:

1. `python eval/select_sample.py` draws 30 documents independently of the
   pipeline: direct Federal Register term searches ("Regulation F", "debt
   collection", "electronic fund transfer", "robocall", "auto loan", 3 each; the
   Section 10 hard-negative topics "mortgage servicing", "overdraft", "personal
   financial data rights", "telemarketing"; and an unfiltered draw), over the same
   agencies, types and window as ingest. At least 5 must be documents the prefilter
   drops, so prefilter misses are measured. It writes blank label rows in shuffled
   order to `labels.csv`, the documents (number, title, agency, date, abstract,
   link) to `eval/candidates.md`, and the query and prefilter decision per
   document to `eval/sample_manifest.csv`. No file carries a relevance judgment.
2. The labeler fills in `labels.csv` **blind**, before seeing triage output or the
   manifest.
3. `python eval/run_eval.py` reports precision, recall, and behavior-class agreement
   (mean Jaccard and exact-match rate) with exact Clopper-Pearson intervals. A
   document the prefilter dropped counts as a "not relevant" prediction, so the eval
   measures prefilter misses too.

**Sample-size caveat.** With about 15 positives, perfect recall has a two-sided 95%
lower bound of 78% (one-sided: 82%). A clean score supports "recall above roughly
80%", not "100%". The script prints the intervals next to every point estimate.

## Provenance method

Each row records **why it is in the register**:
`salient_stated` (named on Salient's public pages), `third_party_stated` (named in a
third-party description of Salient), or `added_by_analysis` (added because the
regulations reach a modeled behavior). The labels follow the BUILD_SPEC inventory.
`provenance_url` is null wherever the specific page was not captured; fill it in
when the page is confirmed. Every row's `source_url` points at primary text where
one is public (eCFR, uscode.house.gov, state legislature sites, FCC documents). For
licensed rulebooks such as Nacha and PCI DSS, it points at the publisher's page.

## Known limits and deferred depth

- **Live ingest has not been run in this build.** The build environment's network
  policy blocked `www.federalregister.gov` and `www.ecfr.gov`, so everything was
  tested against synthetic fixtures. The fixtures are shaped from the documented API
  responses, and real responses may differ in details the fixtures do not capture.
  The first live run is also the first real test of the API field handling and of
  the eCFR amendment-date matching.
- **Triage has not been run.** There is no live triage output, change record, or eval
  result yet.
- **Tier 2 is inventoried, not modeled.** `INSURANCE.CLAIMS` has **no rows**, because
  no primary citations were identified for GAP, appraisal-clause, lien-release or
  CPI rules. Right-to-cure and deficiency rules are covered for MA only. These gaps
  are listed in `research_backlog.yaml` and in INVENTORY.md.
- **Some state citations are placeholders at section level.** For example,
  `MA-940CMR-002` points at 940 CMR 7.04(1) without paragraph-level text. AI
  disclosure rows (CA, UT, CO) describe laws whose scope or effective dates are in
  flux.
- **The prefilter's keyword lists are hand-tuned** and will need adjusting after the
  first live run. Review `dropped.jsonl` for misses.
- **eCFR diffs are section-level text diffs.** They do not interpret the change, and
  a rule that takes effect in stages may produce `no_matching_ecfr_version` for some
  of its dates.

## How the adapter plugs into a real deployment

`adapter/deployment_map.template.yaml` lists every behavior class with blank
`owning_system`, `config_ref`, `test_suite_ref` and `approver_role`. A deploying team
copies it into its own repository and fills it in. Each change record names the
affected behavior classes and asks four standard questions: owning config or script,
approver, rollout sequence, and test evidence. The filled map answers the first two
directly and points at the evidence for the fourth. Nothing in this repository reads
the filled map. The next step is a small consumer that pre-fills those answers in
each record.
