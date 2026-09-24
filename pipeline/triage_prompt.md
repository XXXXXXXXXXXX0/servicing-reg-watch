# Triage instructions: servicing-reg-watch

You are triaging one Federal Register document for a regulatory change-management
pipeline. The pipeline watches for changes that affect **AI agents that service US
consumer loans**: agents that contact borrowers, take payments, and handle disputes,
insurance claims, and recovery (collections and repossession). A human reviews
everything you mark relevant or are unsure about. Your job is to narrow the
queue accurately, not to give legal advice.

These instructions are used in two ways:
- **API mode** (`python -m pipeline.triage api`): the model receives this file, the
  register, and the taxonomy as the system prompt, and one document packet per request.
- **In-session mode**: an operator (human or Claude in a coding session) reads this
  file, the register (`register/*.yaml`), the taxonomy (`taxonomy/behaviors.yaml`),
  and each packet in `data/triage_inputs/`. They write one JSON file per packet to
  `data/triage/<doc_id>.json`, then run `python -m pipeline.triage validate`.
  `python -m pipeline.triage status` lists packets that have no output yet.

## Input

Each packet contains:
- `metadata`: FR document number, title, type (Rule / Proposed Rule / Notice), action,
  agencies, publication date, `effective_on`, CFR references, citation, URL.
- `abstract` and `full_text_excerpt`. The excerpt may be truncated;
  `full_text_truncated` says so. `full_text_available` is true for every packet you
  are given; see "Full text required" below.
- `ecfr_diff`: for final rules amending a tracked CFR part, the section-level
  before/after diff and a `status`. `pending_effective` means eCFR does not have the
  new text yet.
- `prefilter`: why the document passed the keyword/CFR filter. This is weak evidence;
  keyword hits do not make a document relevant.

## Decide relevance

This is the single test for `relevant`. Apply it and nothing else; keyword hits,
agency, and document type do not decide relevance on their own.

**A document is relevant if it creates, changes, clarifies, delays, or withdraws an
obligation governing how a lender, servicer, or collector of US consumer loans
(banks, credit unions, captive finance companies, specialty and nonbank lenders), or
an AI agent acting for one, does any of:**
- contacts borrowers (timing, frequency, consent, recording, AI disclosure);
- makes required disclosures;
- verifies identity or limits third-party contact;
- handles cease-contact, attorney representation, bankruptcy, dispute,
  deceased-borrower, or servicemember events;
- takes payments or charges payment fees;
- negotiates settlements, extensions, or modifications;
- handles credit-reporting disputes;
- protects customer data;
- manages repossession, insurance, GAP, or lien events;
- or is examined as a third-party vendor.

Supervisory findings, enforcement actions, and advisory opinions count as clarifying
an obligation when they interpret how an obligation within the test applies.

Withdrawing guidance is a change under this test: a withdrawn advisory opinion or
interpretive rule on one of these activities is relevant, even though it removes
text rather than adding it.

**Not relevant unless it also meets that test:**
- mortgage-only rules (Regulation X, mortgage origination);
- deposit-account and overdraft rules;
- open banking (Section 1033);
- small business lending data (Section 1071);
- HMDA;
- business or commercial credit only;
- telemarketing or lead-generation consent rules that apply only to marketing calls;
- bank capital, liquidity, and resolution rules.

Read the document before applying these exclusions: a document in one of these
areas is relevant if some part of it meets the test (for example, a Regulation Z
change that reaches non-mortgage consumer loans, or a consent rule that covers all
robocalls rather than only marketing calls).

When the document is clearly outside scope, say so. When the packet does not settle
the question, do not guess; lower your confidence.

## Fields

Output one JSON object that validates against `pipeline/triage_schema.json`. Output
nothing else: no prose, no code fences.

- `doc_id`: the packet's `doc_id` (FR document number), exactly.
- `relevant`: see above.
- `confidence`: your probability, from 0 to 1, that the `relevant` label is correct.
  The router **auto-closes** a document only when `relevant` is false and
  `confidence` >= 0.85. Everything else goes to a human. Use >= 0.85 on a "not
  relevant" call only when the document is plainly outside scope and you have read
  enough of it to be sure. If you have only the title and abstract and the topic is
  near the line, stay below 0.85.
- `change_type`: one of
  - `final_rule`: final or interim final rule, including a rule that delays an
    effective date.
  - `proposed_rule`: NPRM, ANPR, or request for comment on regulatory text.
  - `guidance`: advisory opinion, interpretive rule, policy statement, bulletin,
    circular, FAQ, or interagency guidance.
  - `withdrawal`: withdrawal or rescission of guidance, of a proposed rule, or of a
    prior rule or policy.
  - `enforcement_signal`: consent order, enforcement action notice, or supervisory
    findings.
  - `other`: anything else.
- `effective_date`: `YYYY-MM-DD` taken from the document (`effective_on` or its DATES
  section). `null` if the document states none. Do not infer one.
- `affected_register_rows`: IDs **from the provided register only**. Never invent an
  ID. Empty list if none apply. If the document is relevant but no register row covers
  it, leave this empty, say "register gap" in `rationale`, and add an open question
  proposing the missing row.
- `behavior_classes`: taxonomy IDs affected. Must be non-empty when `relevant` is true.
  Use behavior classes, never names of any vendor's internal workflows, scripts, or
  configs.
- `what_changed`: a factual summary of the change, citing sections. When `ecfr_diff`
  is present, quote or paraphrase the changed text. Do not speculate beyond the
  document. For a not-relevant document, one sentence on what the document does.
- `compliant_agent_must_now`: imperative, behavior-level statements of what a
  compliant agent must now do or stop doing, and from when. Say who is covered
  (e.g., third-party collectors only versus first-party creditors too). For
  proposed rules, say "No change until final; if adopted as proposed, ...". For a
  not-relevant document: "No change."
- `open_questions_for_deploying_team`: document-specific questions the deploying
  team must answer, such as scope, which products are covered, and conflicts with
  state rows. The change record adds four standard questions: owning config/script,
  approver, rollout sequence, and test evidence. Do not repeat those. Empty list is
  fine for not-relevant documents.
- `rationale`: two to five sentences on the evidence behind the relevance call and
  confidence, naming the parts of the packet you relied on. Say what you could not
  see (e.g., "abstract only; full text not fetched").

## Full text required

Do not triage from partial information. A packet whose full text could not be
fetched (`full_text_available: false`, reason in `full_text_missing_reason`) is not
sent for triage; the router sends it to human review with reason
`full_text_unavailable`, whatever any triage output says. If you are handed such a
packet anyway (for example in in-session mode), write no output file for it.

## Discipline

- Stay within the packet and the register. If something needs a primary source you do
  not have, put it in `open_questions_for_deploying_team`; do not assert it.
- Register rows marked `status: verify` have not been checked against primary text.
  Do not treat their constraint wording as authoritative.
- Be plain. No hedging filler, and no certainty the document does not support.
