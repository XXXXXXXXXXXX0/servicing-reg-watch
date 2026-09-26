# servicing-reg-watch

**Memo: Regulatory change management for AI loan-servicing agents (v1, with v1.1 fixes)**

Built without access to any vendor's systems. Not legal advice.

Every number in this memo comes from [`eval/results.md`](eval/results.md),
[`eval/v1_1_fixes.md`](eval/v1_1_fixes.md), [`eval/v1_1_conflicts.md`](eval/v1_1_conflicts.md),
[`eval/error_analysis.md`](eval/error_analysis.md), [`records/REVIEW_LOG.md`](records/REVIEW_LOG.md),
[`records/REVIEW_QUEUE.md`](records/REVIEW_QUEUE.md), [`PREFILTER.md`](PREFILTER.md) or the
committed data under `data/`.

## Problem

AI agents that service US consumer loans call and text borrowers, take payments, and handle
disputes, insurance claims and recovery. Each of those behaviors is governed by rules that
change. The rules come from the CFPB, FCC, FTC, the bank and credit union regulators, the
states and Nacha. Changes arrive as final rules, proposals, delays, guidance and, just as
important, **withdrawals and rescissions of guidance**. A deploying team needs three things:
to learn about a change quickly, to know which agent behaviors it touches, and to leave an
audit trail showing that a human decided what to do about it.

## What the system does

```
Federal Register API ─► 1 ingest ─► 2 prefilter ─► 3 eCFR diff ─► 4 triage (Stage A, Stage B) ─► 5 route ─► 6 change records
 7 agencies, 24 months    2,203 docs    201 kept       22 diffed      215 triaged                    168 auto-closed   one record per
 (2024-09-23..2026-09-24)                                                                            47 to review      relevant document
```

**Two-stage triage.** Every document that reaches triage is screened in **Stage A** from its
title, abstract, metadata and eCFR diff excerpt. **Stage B** re-reads the saved full text for
every Stage A "relevant" call and every call with confidence below 0.7: 35 documents. Stage B
changed the relevance answer for **4 of 35** (2 not relevant to relevant, 2 relevant to not
relevant). It kept the relevance answer but changed register rows, behavior classes, change
type or effective date for **12 more**. Stage A answers are kept in `data/triage_stage_a/`;
the post-Stage-B answers in `data/triage/` are what routing reads and what the eval scores.

**Routing.** 215 documents were triaged (201 prefilter survivors plus 14 prefilter-dropped
eval documents). **168 were auto-closed**: routing closes a document only when triage says
not relevant *and* confidence is at least 0.85. The other **47 went to the human review
queue** ([`records/REVIEW_QUEUE.md`](records/REVIEW_QUEUE.md)): all 22 documents triage called
relevant, plus 25 not-relevant calls below the confidence bar. **Every document triage called
relevant is routed to human review**; none is closed by the pipeline. Untriaged documents,
documents with invalid triage output and documents without full text also go to review,
never to auto-close.

**Change records.** Each relevant document gets a record in `records/` naming the affected
register rows and behavior classes, what changed, what a compliant agent must now do, the
eCFR diff where there is one, and the questions the deploying team must answer (owning
config or script, approver, rollout sequence, test evidence).

### What is deliberately not automated, and why

- **Approving a change stays human.** The pipeline narrows the queue; a person decides. No
  record is marked done and no register row is changed by the pipeline. Two reasons:
  - *Accountability.* A regulator or auditor will ask who decided that a rule did or did not
    apply and on what basis. That has to be a named person with a sign-off, not a
    confidence score.
  - *Errors multiply at scale.* One wrong call applied to an agent's configuration repeats
    on every borrower contact until someone notices. A human approval step is the cheapest
    place to stop it.
- **Register verification.** Every researched row ships as `status: verify`. Flipping a row
  to `verified` requires a person to read the primary source; the validator rejects
  `verified` without `last_checked`. The rows to check are listed in
  [`VERIFY_CHECKLIST.md`](VERIFY_CHECKLIST.md).
- **Unresearched coverage.** Rows with `status: unresearched` record a known gap and carry
  `citation: null`; the validator rejects a citation on them.
- **Mapping to a deployment.** The adapter ships empty. Only the deploying team knows which
  config or script implements a behavior, and a guessed mapping would be worse than none.
- **State law and Nacha monitoring.** There is no Federal Register feed for these. They are
  `change_source: manual` rows and need a person watching them.

## Human review

- **Reviewer decisions override model outputs in the operational records only.** The model's
  outputs in `data/triage/` and `data/triage_stage_a/` are never edited, and the v1 eval
  scores are unchanged. An override is stored as a `review` entry in
  `records/record_meta.yaml`, applied to the record by `python -m pipeline.records annotate`,
  and **logged in [`records/REVIEW_LOG.md`](records/REVIEW_LOG.md)** with the model's answer,
  the reviewer's decision, the reason, the reviewer and the date.
- **Five overrides so far**, all on 2026-09-26:

  | Document | Model (v1) | Reviewer decision |
  |---|---|---|
  | 2025-22490, NCUA breach-response guidance (eval #12) | Not relevant, 0.75 | Relevant; record created, `interpretation` (open, awaits control-validation sign-off) |
  | 2025-22489, NCUA safeguarding guidelines | Not relevant, 0.75 | Relevant; record created, `interpretation` (open, awaits control-validation sign-off) |
  | 2024-22962, CFPB medical-debt advisory opinion (eval #25) | Relevant, 0.70 | Not relevant; record closed |
  | 2024-27791, applicability-date revision of 2024-22962 | Relevant, 0.70 | Not relevant; record closed to match 2024-22962 |
  | 2024-29292, CFPB Regulation V ANPR on identity theft and coerced debt | Relevant, 0.75 | Not relevant; record closed; on the watch list |

- **Scope of v1 human review.** It covered the 30-document eval set (labeled blind, see
  below) and the documents flagged by the v1.1 conflict check
  ([`eval/v1_1_conflicts.md`](eval/v1_1_conflicts.md)). The rest of the 47-document queue is
  left for the operating team, as it would be in production: most records still await
  sign-off.
- The v1.1 change-type and class re-tagging (below) is applied to records as metadata in
  `records/record_meta.yaml`, not as a review override; the model outputs keep their v1
  values there too.

## Sources and data

- **Ingest.** Federal Register API, 7 agencies, rules, proposed rules and notices,
  2024-09-23 to 2026-09-24: 2,203 documents. Queries run per agency and month;
  `data/raw/ingest_manifest.json` records reported and retrieved counts for every chunk, so
  completeness is checkable.
- **Prefilter** ([`PREFILTER.md`](PREFILTER.md)). The original spec only asked for a "cheap
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
    every one of the 73 register rows and 17 behavior classes is reachable by some rule.
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
- **Engineering rules** ([`CLAUDE.md`](CLAUDE.md)): repo-committed caching, no refetching of
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
  (state credit reporting laws, `unresearched`). The three cited rows are cited to committed
  Federal Register text and remain `verify`; their statute and eCFR text has not been read.

## Eval

Protocol (BUILD_SPEC Section 10). 30 documents were drawn by
[`eval/select_sample.py`](eval/select_sample.py) from **direct Federal Register term
searches**, independent of the prefilter, with at least 5 prefilter-dropped documents
required. The labeler filled in `eval/labels.csv` **blind to triage outputs** and to the
selection manifest. A prefilter drop counts as a "not relevant" prediction, so prefilter
misses are measured.

**Sample: 6 labeled relevant, 24 labeled not relevant.**

| | Labeled relevant | Labeled not relevant |
|---|---|---|
| Predicted relevant | TP 5 | FP 1 |
| Predicted not relevant | FN 1 | TN 23 |

Exact (Clopper-Pearson) two-sided 95% intervals:

| Metric | Raw | Point | 95% interval |
|---|---|---|---|
| Precision (end to end) | 5/6 | 83.3% | 35.9% to 99.6% |
| Recall (end to end) | 5/6 | 83.3% | 35.9% to 99.6% |
| Specificity (end to end) | 23/24 | 95.8% | 78.9% to 99.9% |
| Prefilter recall | 6/6 | 100.0% | 54.1% to 100.0% |

Triage alone gives the same counts, because no relevant document was dropped by the prefilter.

- **Specificity is the most robust measure** here: it rests on 24 negatives, and its interval
  is the only narrow one. Precision and recall rest on 6 documents each; one error moves
  either by 16.7 points, and the intervals run from about 36% to nearly 100%.
- **The prefilter kept all 6 relevant documents**, although **14 of the 30** eval documents
  were ones it dropped (the manifest, recomputed from committed metadata: 16 keep, 14 drop).
  Perfect prefilter recall on 6 positives still only supports a lower bound of 54.1%.
- **Stage B fixed one error and caused one on this sample.** Stage A alone would have given
  the same counts: Stage B fixed 2024-30824 (not relevant to relevant) and introduced the
  2025-22490 miss (relevant to not relevant). So Stage B's value does not show in relevance
  accuracy on this sample. It shows in the **specificity of the change records**: 12 of its
  35 reads corrected the rows, classes, change type or effective date that the records carry.
- **Behavior-class tagging over-included secondary classes.** On the 5 true positives, 12 of
  14 labeled classes were predicted, but only **12 of 17 model tags** matched a label (mean
  Jaccard 0.62; exact set match 2 of 5). The extra tags were classes a document touches
  without changing what the agent must do. v1.1 separates **primary** tags (drive routing and
  review) from **secondary** context tags.
- Tier agreement was not scored: no labeled document has a tier.

## What the eval revealed

Root-cause analysis: [`eval/error_analysis.md`](eval/error_analysis.md). Fixes:
[`eval/v1_1_fixes.md`](eval/v1_1_fixes.md). Both model errors were gaps in the relevance test
in `pipeline/triage_prompt.md`, not prefilter drops.

| Error | Document | Root cause | v1.1 fix |
|---|---|---|---|
| False negative | 2025-22490: NCUA proposal to remove Appendix B (breach-response guidance) from 12 CFR 748 and reissue it as a Letter to Credit Unions. Stage A said relevant (0.6); Stage B reversed it (0.75). | The test covered *withdrawn* guidance but not guidance moved out of the CFR with its text unchanged, so Stage B relied on the document's own "no substantive change" statement. | A change in an obligation's **legal status** (codified, moved out of the CFR into guidance or back, removed) is relevant even if its text is unchanged. It routes as the new change type `interpretation` (control validation). |
| False positive | 2024-22962: CFPB advisory opinion on medical-debt collection under FDCPA / Regulation F (later withdrawn by 2025-08286). | Advisory opinions counted as clarifying whenever they interpret an obligation in scope, and Regulation F governs loan collectors too. Nothing excluded guidance aimed at a non-loan debt type or guidance that only restates existing law. | Guidance limited to a **non-loan debt type** is not relevant unless it states a rule for consumer-loan collection generally. Guidance that only **restates existing law** routes as `interpretation`, not as a behavior change. |
| Class over-tagging | 5 true positives, 17 predicted classes vs. 14 labeled | No distinction between classes a document changes and classes it merely touches. | `behavior_classes_primary` and `behavior_classes_secondary` in the prompt, schema and validator; v1 outputs still validate. |

**The v1.1 clarifications were added after scoring and have not been tested on a fresh eval
set.** The v1 scores are final and were not changed; relevance triage was not re-run.
Re-scoring the 30 documents the fixes were derived from would be circular. Other v1.1 rules
added at the same time: judge a document by its ACTION line and substance rather than its
Federal Register type label; ask whom a rule binds; treat ANPRs without proposed text as not
relevant.

**Conflicts** ([`eval/v1_1_conflicts.md`](eval/v1_1_conflicts.md)). All 215 v1 outputs were
read against the v1.1 rules without re-triaging.

- **5 relevance conflicts**, each resolved in human review (see the Human review table):
  2024-22962 and 2024-27791 closed as not relevant (non-loan debt type); 2024-29292 closed as
  not relevant (ANPR, no proposed text) and put on the watch list; 2025-22490 and 2025-22489
  given records as `interpretation` (legal-status change).
- **4 change-type conflicts** on documents that stay relevant: Supervisory Highlights Auto
  Finance (2024-24093), Student Lending (2024-30758) and Issue 37 (2024-31670), and the CFPB
  FCRA preemption interpretive rule (2025-19671). Their records now route as `interpretation`;
  the model outputs keep their v1 type.
- The same file lists near-the-line documents that v1.1 confirms (for example, FCC
  call-blocking duties that bind carriers, not callers; regulatory agendas; ANPRs).

## Lessons for AI servicing agents

- **Automated dispute handling needs the system of record.** CFPB Supervisory Highlights,
  Issue 37 (2024-31670) found debt-collector furnishers verifying indirect disputes through
  **automated systems that checked only their own records**, not their creditor clients'
  records, and deleting tradelines by default when clients did not respond (FCRA
  1681s-2(b)(1)). An AI agent that resolves disputes against its own data store repeats that
  finding at scale.
- **Withdrawn guidance changes enforcement posture, not the law.** FR 2025-08286 withdrew 67
  CFPB guidance documents, including Regulation F, FCRA and repossession items. The
  underlying statutes and regulations still apply as written, and courts, state regulators,
  other federal regulators and private plaintiffs can still apply the same readings; the
  CFPB also said the withdrawal may not be final. The record's instruction is to re-map each
  control to its statutory source, not to relax it.

## Design choices

- **Each document is judged as published.** A later withdrawal, disapproval or vacatur does
  not rewrite the earlier triage. It is linked instead: records carry `supersedes` and
  `superseded_by` (in `records/record_meta.yaml`), and a withdrawal, final rule, disapproval
  or vacatur closes or reverses the earlier record, while an amendment or correction leaves
  it open. Seven records were closed this way; for example, 2025-08286 closes 2024-22962 and
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
  (`taxonomy/behaviors.yaml`, 17 classes). The pipeline never names or guesses at a vendor's
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

## Limitations

- **Court decisions are visible only through the agency.** A vacatur or injunction reaches
  the Federal Register only if the agency publishes a notice (as the FCC did in 2025-16641
  after the one-to-one consent vacatur). Court dockets are not monitored.
- **State-varying rules are mapped but unresearched.** Multi-state topics (GAP and add-on
  refunds, appraisal-clause deadlines, lien release, collateral protection insurance, state
  credit reporting laws) are register rows with `status: unresearched` or, for GAP, a federal
  supervisory citation only. **No citation was filled from memory**; the gaps are in
  `register/research_backlog.yaml` and INVENTORY.md.
- **Register rows are unverified.** 69 of 73 rows are `verify` and none is `verified`; most
  were drafted from working knowledge without the primary text open. See
  [`VERIFY_CHECKLIST.md`](VERIFY_CHECKLIST.md).
- **Small eval sample.** 6 positives and 24 negatives. The intervals above are the honest
  summary, and the v1.1 fixes are unmeasured.
- **How v1 triage was run.** v1 triage (Stage A and Stage B) was performed by Claude in an
  agent session, following `pipeline/triage_prompt.md` and writing outputs that pass the same
  validator. It is reproducible with an API key via `pipeline/triage.py`
  (`python -m pipeline.triage api`, `ANTHROPIC_API_KEY`), but the committed outputs were not
  produced that way, and a re-run will not match them exactly.
- **Partial reads.** Stage B read at most about 4,000 words; 26 of 35 reads were partial
  (logged per document).
- **Built without access to any vendor's systems.** The deployment adapter
  (`adapter/deployment_map.template.yaml`) is deliberately empty: connecting behavior classes
  to real configs, scripts, test suites and approvers needs internal context.
- **Tier 2 is inventoried, not modeled.** INSURANCE.CLAIMS has only the multi-state rows
  above.

## Watch list and future work

- **FCC onshoring NPRM (FR 2026-07960).** Triaged not relevant (0.80): its proposals bind
  communications providers' customer-service call centers. But it asks whether to extend some
  or all of its proposals to **all calls covered by TCPA sections 227(c) and (d) that
  originate outside the United States**, which include telephone solicitations and
  artificial or prerecorded-voice calls from foreign call centers. If adopted that way, it
  would reach lenders' offshore calling. It is in the review queue as a low-confidence
  not-relevant call.
- **CFPB coerced-debt ANPR (FR 2024-29292).** Closed as not relevant (no proposed text), but
  the CFPB states a rulemaking is warranted to bring coerced debt into Regulation V's
  identity-theft definitions, which signals future **identity-theft block** obligations for
  furnishers.
- **The Unified Agenda as an early-warning source.** Regulatory agendas (for example, 2026-16615
  and 2026-16617) are correctly not relevant as documents, but they list planned actions
  months ahead. A future step would parse them for register topics and put matches on the
  watch list.
- **A larger held-out eval set** to test v1.1: newly drawn and blind-labeled, not the 30
  documents the fixes came from, with enough positives to narrow the recall interval.
- Sign off control validation on 2025-22490 and 2025-22489; work the rest of the review queue;
  verify the register rows.

## How the adapter plugs into a real deployment

`adapter/deployment_map.template.yaml` lists every behavior class with blank
`owning_system`, `config_ref`, `test_suite_ref` and `approver_role`. A deploying team copies
it into its own repository and fills it in. Each change record names the affected behavior
classes and asks four standard questions: owning config or script, approver, rollout
sequence and test evidence. The filled map answers the first two directly and points at the
evidence for the fourth. Nothing in this repository reads the filled map yet; the next step
is a small consumer that pre-fills those answers in each record.

## Repository map and quick start

| Path | What it is |
|---|---|
| `register/federal.yaml`, `register/states/*.yaml` | Register rows (73). `register/INVENTORY.md` is generated from them. |
| `taxonomy/behaviors.yaml` | 17 behavior classes and the `applies_to` vocabulary. |
| `pipeline/` | `ingest`, `prefilter`, `diff`, `triage`, `route`, `records`, `inventory`, `run`. |
| `pipeline/triage_prompt.md`, `pipeline/triage_schema.json` | Triage instructions (v1.1) and output schema. |
| `data/raw/`, `data/triage/`, `data/triage_stage_a/` | Committed cache and in-session triage outputs. |
| `records/` | Change records, `REVIEW_QUEUE.md`, `REVIEW_LOG.md`, `record_meta.yaml`. |
| `eval/` | Sample selection, blind labels, results, error analysis, v1.1 fixes and conflicts. |
| `adapter/deployment_map.template.yaml` | Empty deployment adapter interface. |
| `fixtures/` | **Synthetic** API responses and triage outputs for offline tests. |

```bash
pip install -r requirements.txt                 # + requirements-api.txt for API triage
python -m pytest -q                             # offline; sockets are blocked in tests
python -m pipeline.run --offline --with-fixture-triage --data-dir /tmp/srw/data --records-dir /tmp/srw/records

python -m pipeline.run                          # live: ingest → prefilter → text → diff → triage inputs → route → records
python -m pipeline.triage api                   # API-mode triage (ANTHROPIC_API_KEY)
python -m pipeline.triage validate              # check triage JSON against the schema and register
python -m pipeline.records annotate             # apply record_meta.yaml (supersession, v1.1 tags, reviews)
python eval/run_eval.py                         # regenerate eval/results.md
```
