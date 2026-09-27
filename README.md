# servicing-reg-watch

**Turning regulatory changes into specific, human-approved instructions for AI agents across
loan servicing, collections, recovery, insurance claims, and disputes.**

Built without access to any vendor's systems. Not legal advice. Every number below is taken
from a file in this repository, linked where it is used.

## Summary

**What this is.** A pipeline that reads the Federal Register, finds the changes that touch
what an AI servicing agent does (calls, texts, payments, disputes, repossession, claims),
and writes a change record for each one: which obligations moved, what a compliant agent
must now do, and the questions the deploying team must answer before it changes anything.
A register of 92 obligations (federal, six states and multistate topics) anchors every call to a cited
source.

**Results.**
- **3,683 documents ingested**, 2024-09-23 to 2026-09-24 (eight agencies, including the
  Defense Department for the Military Lending Act). **206 kept** by the prefilter.
- **220 triaged** (the 206 plus 14 eval documents the prefilter dropped). **171
  auto-closed**, **49 routed to human review**, 27 change records written
  ([`records/REVIEW_QUEUE.md`](records/REVIEW_QUEUE.md)).
- **v1 eval** on 30 blind-labeled documents (6 relevant, 24 not)
  ([`eval/results.md`](eval/results.md)): specificity **23/24 (95.8%)**, precision **5/6
  (83.3%)**, recall **5/6 (83.3%)**. The precision and recall intervals run from 35.9% to
  99.6%; six positives cannot say more.

**Judgment calls.**
- **Humans approve every change.** The pipeline narrows the queue and drafts the
  instruction; a named person signs it off.
- **Interpretive guidance routes to control validation**, not behavior change: supervisory
  findings and interpretive rules mean "check your controls against this reading."
- **Withdrawn guidance changes enforcement posture, not the law.** The statute still
  applies, so controls are re-mapped to it, not relaxed.

**Status.** v1 is scored and final. The v1.1 fixes and the v1.2 scope expansion are
**untested on a fresh eval set**. Register verification
([`register/VERIFICATION_REPORT.md`](register/VERIFICATION_REPORT.md)): 69
`machine_verified`, 1 hand-verified, 15 `verify`, 7 `unresearched`.

## What is deliberately not automated, and why

- **Approving a change.** No record is marked done and no register row is changed by the
  pipeline. *Accountability:* an examiner will ask who decided a rule did or did not apply,
  and that must be a named person, not a confidence score. *Errors multiply at scale:* one
  wrong call in an agent's configuration repeats on every borrower contact; a human
  approval step is the cheapest place to stop it.
- **Closing anything uncertain.** Only a "not relevant" call at confidence 0.85 or higher is
  auto-closed. Everything triage calls relevant, everything below the bar, and anything
  with missing text or invalid output goes to review.
- **Register verification.** A machine check becomes `machine_verified` only when the
  reviewer accepts it; `verified` means the reviewer read the source by hand.
- **Mapping to a deployment.** The adapter
  ([`adapter/deployment_map.template.yaml`](adapter/deployment_map.template.yaml)) ships
  empty. Only the deploying team knows which config or script implements a behavior; a
  guessed mapping is worse than none.
- **State law and Nacha monitoring.** No feed exists; these rows are `change_source:
  manual` and need a person watching them.

## Pipeline

```
Federal Register API ─► 1 ingest ─► 1b disapproval check ─► 2 prefilter ─► 3 eCFR diff ─► 4 triage (A, B) ─► 5 route ─────────► 6 records
 8 agencies, 24 months   3,683 docs   305 public laws,         206 kept      22 diffed      220 triaged        171 auto-closed    27 change
 2024-09-23..2026-09-24               23 CRA disapprovals,     + 14 eval     (72 cite a     Stage B: 37        49 to review       records
                                      3 match the store        docs the      tracked part)  full-text reads
                                                               prefilter dropped
```

The 14 prefilter-dropped eval documents were triaged only so the eval measures prefilter
misses. Prefilter rules and results:
[`PREFILTER.md`](PREFILTER.md). Sources, diff coverage and partial reads:
[`docs/DETAILS.md`](docs/DETAILS.md).

### Two-stage triage

**Stage A** screens every document from its title, abstract, metadata and eCFR diff.
**Stage B** re-reads the saved full text for every Stage A "relevant" call and every call
below 0.7 confidence. In v1 that was 35 documents:
- Stage B changed the relevance answer on **4 of 35** (2 each way).
- It kept the answer but corrected register rows, behavior classes, change type or
  effective date on **12 more**. That is where its value shows: in what the records tell
  the agent to do.
- On the eval sample it fixed one error (2024-30824) and caused one (2025-22490), so it
  did not move relevance accuracy.
- Stage B reads at most about 4,000 words; 26 of the 35 reads were partial (logged per
  document).

v1.2 added 2 Stage B reads (both NCUA part 749 documents, full text), for 37.

### Human review scope

Review covered the **30-document eval set** and the **documents flagged by the v1.1 and
v1.2 conflict checks** ([`eval/v1_1_conflicts.md`](eval/v1_1_conflicts.md),
[`eval/v1_2_conflicts.md`](eval/v1_2_conflicts.md)), plus the two new NCUA documents. The
rest of the 49-document queue is left to the operating team, as it would be in
production. Reviewer decisions override model outputs **in the operational records only**;
the model outputs in `data/triage/` and the v1 scores are never edited. Every decision is
logged with the model's answer, the decision, the reason, the reviewer and the date:
22 entries in [`records/REVIEW_LOG.md`](records/REVIEW_LOG.md).

## Product lines, segments and priority (v1.2)

- **Six product lines** ([`taxonomy/product_lines.yaml`](taxonomy/product_lines.yaml)):
  servicing, collections, recovery, insurance claims, disputes, compliance audit, mapped
  many-to-many to 20 behavior classes.
- **Four segments** ([`taxonomy/segments.yaml`](taxonomy/segments.yaml)): bank, credit
  union, captive, specialty lender. Each register row binds, does not bind, or is
  `unclear` for each segment; `unclear` is never resolved by guessing.
- **Priority.** A record is `high` when a primary class runs on every contact or
  transaction (CONTACT.\*, DISCLOSURE.REQUIRED, IDENTITY.RIGHT_PARTY, STOP.TRIGGERS,
  PAYMENT.\*) or is DISPUTES.ERROR_RESOLUTION (fixed statutory deadlines on every dispute).
  The queue is sorted by priority, then product line
  ([`records/BY_PRODUCT_LINE.md`](records/BY_PRODUCT_LINE.md),
  [`records/BY_SEGMENT.md`](records/BY_SEGMENT.md)).
- **Scope expansion.** 18 register rows (error resolution, card claims and defenses, the
  Military Lending Act, Red Flags, the Holder Rule, record retention, payoff and GAP),
  new prefilter parts and keywords, and a Defense Department ingest.
- **Result.** **5 new documents kept** (FDIC 2, NCUA 3). **Triage called none relevant:**
  3 auto-closed; the 2 NCUA part 749 documents (0.75) went to review, where the reviewer
  judged them relevant as a legal-status change and gave them `interpretation` records.
  **The Defense Department ingest (1,480 documents) kept none.** None of this is measured
  by the v1 eval.

## v1 eval

30 documents were drawn from direct Federal Register term searches, independent of the
prefilter, with prefilter-dropped documents required; the labeler was blind to triage. A
prefilter drop counts as "not relevant", so prefilter misses are measured.

| | Labeled relevant | Labeled not relevant |
|---|---|---|
| Predicted relevant | TP 5 | FP 1 |
| Predicted not relevant | FN 1 | TN 23 |

| Metric | Raw | Point | Exact 95% interval |
|---|---|---|---|
| Specificity | 23/24 | 95.8% | 78.9% to 99.9% |
| Precision | 5/6 | 83.3% | 35.9% to 99.6% |
| Recall | 5/6 | 83.3% | 35.9% to 99.6% |
| Prefilter recall | 6/6 | 100.0% | 54.1% to 100.0% |

- **Specificity is the only robust number.** One error moves precision or recall by 16.7
  points.
- **The prefilter kept all 6 relevant documents**, though it dropped 14 of the 30.
- **Class tagging over-included:** 12 of 17 model class tags matched a label (mean
  Jaccard 0.62).

### Error root causes and v1.1 fixes

Both errors were gaps in the relevance test, not prefilter drops
([`eval/error_analysis.md`](eval/error_analysis.md), [`eval/v1_1_fixes.md`](eval/v1_1_fixes.md)).

| Error | Document | Root cause | v1.1 fix |
|---|---|---|---|
| False negative | 2025-22490: NCUA moves breach-response guidance out of the CFR, text unchanged | The test covered withdrawn guidance, not guidance moved out of the CFR; Stage B trusted the "no substantive change" statement. | A change in an obligation's **legal status** is relevant even with unchanged text; routes as `interpretation`. |
| False positive | 2024-22962: CFPB medical-debt advisory opinion (Regulation F) | Nothing excluded guidance aimed at a non-loan debt type. | Guidance limited to a **non-loan debt type** is not relevant; guidance that only restates law routes as `interpretation`. |
| Class over-tagging | 17 tags vs. 14 labels on 5 true positives | No split between classes changed and classes touched. | **Primary** and **secondary** class tags. |

The fixes were written after scoring and **have not been tested on a fresh set**;
re-scoring the 30 documents they came from would be circular.

## Register verification

Full detail: [`register/VERIFICATION_REPORT.md`](register/VERIFICATION_REPORT.md).
`pipeline/verify.py` fetched primary text (eCFR, GovInfo, U.S. Code, state statutes) into
the committed store and compared each cited row with it; the reviewer then accepted or
overrode each result.

- **92 rows: 69 `machine_verified`, 1 hand-verified (MA-940CMR-001, whose source site
  refuses automated requests), 15 `verify`, 7 `unresearched`.**
- **Six mismatches found.** Five rows were corrected to the fetched text and re-checked
  as matches:
  - **CA-ROSENTHAL-001:** the row said the FDCPA's disclosure rules reach first-party
    lenders in California. Cal. Civ. Code 1788.17 exempts first-party creditors from
    1692e(11) and 1692g, and incorporates the FDCPA as of January 1, 2001, not
    Regulation F. Timing, third-party and cease rules do reach them.
  - REGF-STOP-003 (cited 1006.38(d) only; (c) also applies), REGZ-MOD-001 (conditions of
    1026.20(a)(4) dropped), UDAAP-INS-001 (an abusiveness finding labeled unfair),
    FL-FCCPA-004 (narrower than 559.72(5)).
  - The sixth, **FCRA-MEDINFO-001**, was not a row error: eCFR still shows the vacated 2025
    medical-information amendment. The reviewer kept the row by override; it stays
    `verify`.
- **Preemption, 59 federal rows:** 33 **floor** (stricter state law allowed, e.g.
  Regulation F, UDAAP, MLA), 6 **express preemption** (FCRA furnisher duties and Red Flags
  under 15 USC 1681t, E-SIGN, Regulation Z billing-error procedures), 3 **mixed** (TCPA
  227(f)(1)), 8 with no provision stated, 9 not applicable (private rules, guidance). Of
  36 state-federal pairs, 1 is stricter (Massachusetts' two-calls-in-seven-days rule),
  28 differ in scope (mostly by reaching first-party creditors), 4 are not stricter, 3
  unclear. No automatic conflict resolution is built.

## Lessons for AI servicing agents

- **Automated dispute handling needs the system of record.** CFPB Supervisory Highlights
  Issue 37 (2024-31670) found furnishers verifying indirect disputes through **automated
  systems that checked only their own records**, not their creditor clients', and deleting
  tradelines by default when clients did not respond. An AI agent that resolves disputes
  against its own data store repeats that finding at scale.
- **Guidance withdrawals change enforcement posture, not the law.** FR 2025-08286 withdrew
  67 CFPB guidance documents. The statutes and regulations still apply, and courts, states,
  other regulators and private plaintiffs can still apply the same readings. The record
  says to re-map each control to its statutory source, not to relax it.
- **Checking against eCFR is necessary but not sufficient.** eCFR lagged two legal events:
  the **overdraft rule** (2024-29699), disapproved by Congress in P.L. 119-10, still shows
  as 12 CFR 1026.62; the **medical-information rule** (2024-30824), vacated by a federal
  court on July 11, 2025 (the reviewer's source; not fetched here), still shows 1022.30(d) as [Reserved]. That led to a
  **congressional-disapproval check** (`pipeline/cra.py`, step 1b): 305 public laws in the
  window, 23 Congressional Review Act disapprovals (each confirmed by "no force or effect"
  text), 3 matching stored documents (2024-29699, 2024-27836, 2024-21560). **Court
  vacaturs are still not covered**; the 2024-30824 vacatur was linked by hand.

## Limitations

- **The original register was written before network access**, from working knowledge.
  Rows now cite sources, and verification status is as reported above.
- **State-varying rules are unresearched.** GAP and add-on refunds, appraisal-clause
  deadlines, lien release, collateral protection insurance, state payoff and credit
  reporting rules carry `status: unresearched`. No citation was filled in for these rows
  ([`register/research_backlog.yaml`](register/research_backlog.yaml)).
- **15 rows could not be checked.** Nacha (3) and PCI DSS are proprietary; the other
  sources (Texas statutes, Massachusetts regulations, Colorado, Utah, Federal Reserve
  SR 11-7, AICPA SOC 2) were blocked by this environment's network policy or refused
  automated requests. One Massachusetts row was then checked by hand.
- **Small eval:** 6 positives, 24 negatives.
- **v1.1 and v1.2 are unmeasured** on any held-out set.
- **How v1 triage was run.** Claude performed Stage A and Stage B in an agent session,
  following `pipeline/triage_prompt.md` and passing the same validator. It is reproducible
  via `python -m pipeline.triage api` with an `ANTHROPIC_API_KEY`, but the committed
  outputs were not produced that way and a re-run will not match exactly.
- **Built without access to any vendor's systems**, so the adapter is empty and no real
  agent, script or transcript was tested.

## Future work

- **Interpretations library as a standing control-test suite.** The latest version of each
  supervisory finding, advisory opinion, policy statement and interpretive rule drives
  tests run against the agents; withdrawn guidance is kept, marked advisory-only. Requires
  access to the vendor's agents and transcripts.
- **Court docket monitoring** (CourtListener) to close the vacatur gap.
- **A CFPB enforcement-actions feed** for UDAAP readings that never reach the Federal
  Register.
- **Wider state coverage and preemption-resolution logic**, starting with the thin areas.
- **The Unified Agenda as early warning:** parse planned actions for register topics.
- **A larger held-out eval** covering the v1.2 scope, with enough positives to narrow
  recall.

**Watch list.** The **FCC onshoring NPRM (2026-07960)** asks whether to extend its proposals
to all TCPA-covered calls originating outside the United States, which would reach
lenders' offshore calling. The **CFPB coerced-debt advance notice (2024-29292)** signals
future identity-theft block duties for furnishers.

## Implementation notes

- **eCFR diffs.** Diffs compare eCFR point-in-time text (the day before vs. the effective
  date), not the rule preamble. The step reports `pending_effective`,
  `effective_date_unknown` or `no_matching_ecfr_version` rather than guessing. A live run
  showed appendix amendments (including the Official Interpretations) were silently
  skipped; fetching appendix versions raised diffed documents from 12 to 22.
- **One triage contract.** `pipeline/triage_prompt.md` is the only statement of the triage
  instructions for API and in-session mode alike; both pass the same JSON Schema and
  semantic validator. Invalid output goes to `data/triage/_rejected/`, never the queue.
- **Append-safe records.** A record whose `Reviewer:` line is filled in is never
  overwritten; post-signature metadata lives in `records/record_meta.yaml`.
- **External-source links.** A later withdrawal, disapproval or vacatur does not rewrite an
  earlier triage; it is linked (`supersedes`, `superseded_by`) and closes or reverses the
  record. A court decision, which is not a Federal Register document, is linked as an
  external source.
- Sources, caching, diff coverage, provenance, what testing caught and the adapter:
  [`docs/DETAILS.md`](docs/DETAILS.md).

## Repository map and quick start

| Path | What it is |
|---|---|
| `register/federal.yaml`, `register/states/*.yaml` | 92 register rows; `INVENTORY.md` and `VERIFICATION_REPORT.md` are generated from them. |
| `taxonomy/` | Behavior classes, product lines, segments and priority. |
| `pipeline/` | `ingest`, `cra`, `prefilter`, `diff`, `triage`, `route`, `records`, `inventory`, `verify`, `run`. |
| `data/raw/`, `data/triage/`, `data/triage_stage_a/` | Committed cache and in-session triage outputs. |
| `records/` | Change records, review queue, review log, indexes, `record_meta.yaml`. |
| `eval/` | Sample selection, blind labels, results, error analysis, fixes and conflicts. |
| `adapter/` | Empty deployment adapter interface. |
| `fixtures/` | **Synthetic** API responses and triage outputs for offline tests. |

```bash
pip install -r requirements.txt -r requirements-api.txt   # same packages as CI
python -m pytest -q                                       # offline; sockets are blocked in tests
python -m pipeline.run --offline --with-fixture-triage --data-dir /tmp/srw/data --records-dir /tmp/srw/records

python -m pipeline.run                # live: ingest → disapproval check → prefilter → text → diff → triage inputs → route → records
python -m pipeline.triage api         # API-mode triage (ANTHROPIC_API_KEY)
python -m pipeline.records annotate   # apply record_meta.yaml (supersession, tags, reviews)
python -m pipeline.verify report      # regenerate register/VERIFICATION_REPORT.md
python eval/run_eval.py               # regenerate eval/results.md
```
