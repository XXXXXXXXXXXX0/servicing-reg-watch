# Prefilter rules

The prefilter is step 2 of the pipeline (BUILD_SPEC Section 7). It runs on already-ingested Federal Register metadata (`data/raw/federal_register/*.json`) and fetches nothing. Its job is to cut the ingest down to documents worth triaging, cheaply and auditably. It is not the relevance test; triage makes that call (`pipeline/triage_prompt.md`).

Code: `pipeline/prefilter.py` (rule A's part list is `PREFILTER_CFR_PARTS` in `pipeline/config.py`). Every document gets a decision and a reason code. Drops are logged in full to `data/prefilter/dropped.jsonl`.

Rules are applied in this order. The first rule that decides a document wins.

## 1. Exclude administrative notices

These are dropped **before** any keep rule, even when they cite a tracked CFR part or contain a keyword. They are procedural notices that never change what a lender, servicer or collector must do. Under the old prefilter they got through on incidental keywords (a paperwork notice for a debt-collection survey mentions "debt collection") and filled the review queue.

| Reason code | What is excluded | Matched on | Why |
|---|---|---|---|
| `excluded_pra_information_collection` | Paperwork Reduction Act information-collection notices ("Agency Information Collection Activities", "Information Collection Being Reviewed/Submitted", "Submission for OMB Review", "Proposed Collection; Comment Request") | Title, and only when the type is Notice | These ask for comment on paperwork burden estimates. They create no obligation. The Notice-only condition stops the rule from dropping a rule whose title happens to mention an information collection. |
| `excluded_sunshine_act_meeting` | Sunshine Act meeting notices | Title | These are meeting agendas. Anything decided at the meeting is published separately. |
| `excluded_privacy_act_sorn` | Privacy Act of 1974 system-of-records notices | Title ("Privacy Act of 1974", "system of records") | These cover an agency's own records about people, not duties of regulated lenders. |
| `excluded_agency_organization` | Agency organization or delegation notices ("Delegation(s) of Authority", "Statement of Organization", "Organization and Functions", "Agency Organization", "Rules of Organization") | Title | These are about the agency's internal structure. |
| `excluded_fcc_spectrum_broadcast_licensing` | FCC spectrum, broadcast and licensing items (spectrum, broadcast, television, radio service, FM/AM/LPFM, licens-, auction, satellite, antenna, amateur radio, table of allotments, MHz/GHz) | Title, FCC documents only. Acronyms are case-sensitive. | This is most of the FCC's Federal Register volume and none of it touches consumer contact. The TCPA items that matter are not licensing items and are unaffected. The Wireless Telecommunications Bureau's name is deliberately **not** on the list, because that bureau also issues robocall items. |

## 2. Keep

A document that is not excluded is kept if **any** of A, B or C matches. The reason code names the first one that matches. The hits for all three are logged.

### A. CFR match (`A_cfr_part`)

The document's own `cfr_references` metadata includes one of these parts. If the metadata has no CFR references, rule A does not apply. CFR parts are never inferred from the agency, the title or anything else.
- 12 CFR 1002 (Reg B), 1005 (Reg E), 1006 (Reg F), 1016 (Reg P), 1022 (Reg V), 1026 (Reg Z)
- 47 CFR 64 (TCPA rules are in 64.1200)
- 16 CFR 314 (FTC Safeguards Rule)
- 12 CFR 30 (OCC), 208 (Fed), 225 (Fed), 364 (FDIC), 748 (NCUA): bank and credit union information-security standards, security programs and incident notification
- 12 CFR 53 (OCC) and 304 (FDIC): computer-security incident notification
- 12 CFR 1090 (CFPB): larger-participant rules, which bring nonbank auto lenders, collectors and payment companies under CFPB supervision

**Why:** these are the parts that hold the register's federal rules, plus the parts that decide who is supervised for them. A document that amends one of them changes rule text that a servicing agent follows, or changes who has to follow it. It is kept whatever its title says. The list is a minimum, and the prefilter leans toward keeping: parts are added freely and removed only with a stated reason.

### B. CFPB document type (`B_cfpb_type`)

The document is from the CFPB and is one of:
- a final rule (type Rule) or a proposed rule (type Proposed Rule)
- an interpretive rule, advisory opinion, policy statement (or "statement of policy"), or Supervisory Highlights
- a withdrawal or rescission of guidance (a withdraw/rescind/rescission/revocation word together with a guidance word: guidance, interpretive, advisory opinion, policy statement, circular, bulletin, interpretation)

The guidance types and the withdrawal test are matched against the title, the FR `action` field and the abstract. The abstract is included because the document type is sometimes stated only there (e.g., "This policy statement…").

**Why:** the CFPB is the primary regulator for most of the register. Its rules and guidance, and its withdrawals of guidance, change obligations even when the title uses none of the keywords (e.g., "Rules of Practice for Adjudication Proceedings"). Withdrawals count as changes (BUILD_SPEC Section 3). Withdrawals by other agencies are not kept on that basis alone. They need an A or C match.

### C. Keyword in title or abstract (`C_keyword`)

**Why:** this catches documents from any agency that bear on a register topic without citing a tracked CFR part. Examples are FTC and FCC items, bank-regulator guidance, and supervisory material.

Matching:
- Whole words or phrases, not substrings. For example, `ACH` does not match "Achieving" and `bot` does not match "Robot".
- An optional plural `s`/`es` is allowed on the last word ("servicers", "robocalls").
- Terms marked `*` are stems and match any ending ("delinquen*" matches delinquent and delinquency).
- A hyphen and a space are interchangeable ("third-party" = "third party").
- `ACH`, `UDAAP`, `GAP` (in "GAP waiver"), `E-SIGN`, `SOC 2` and `PCI DSS` are case-sensitive. Everything else is case-insensitive.

Keywords from the rule:

debt collection; debt collector; servicing; servicer; delinquen*; loan modification; deferral; forbearance; auto loan; automobile; motor vehicle; vehicle financ*; repossession; right to cure; deficiency; guaranteed asset protection; GAP waiver; add-on product; collateral protection insurance; force-placed; lien release; total loss; Telephone Consumer Protection Act; robocall; autodialer; automatic telephone dialing; artificial voice; prerecorded; revoke consent; revocation of consent; text message; call recording; recorded call; validation notice; electronic signature; E-SIGN; electronic fund transfer; preauthorized; Regulation E; ACH; convenience fee; pay-to-pay; furnisher; credit reporting; Regulation V; Regulation P; privacy notice; safeguards; information security; data breach; unfair, deceptive, or abusive; UDAAP; Equal Credit Opportunity; Regulation B; servicemember; bankruptcy; deceased; cease communication; third-party relationship; third-party risk; service provider; model risk; artificial intelligence; chatbot.

**Added by coverage check** (see below). Each one closes a gap where a register row was reachable through no rule-A part and no keyword above:

| Keyword | Register rows it reaches |
|---|---|
| unfair or deceptive | FTC5-001 (FTC Act §5: "unfair or deceptive acts or practices") |
| collection practices | FL-FCCPA-001 to 004 (Florida Consumer Collection Practices Act) |
| recording | CA-REC-001, FL-REC-001, MA-REC-001 (call-recording consent) |
| wiretap | MA-REC-001, TX-REC-001 (Massachusetts Wiretap Act, Texas wiretap statute) |
| bot | CA-AIDISC-001 (California BOT Disclosure Law) |
| Nacha | NACHA-TEL-001, NACHA-WEB-001 (Nacha Operating Rules) |
| SOC 2 (case-sensitive) | SOC2-001 |
| PCI DSS (case-sensitive) | PCI-001 |

## 3. Drop everything else (`no_match`)

Anything not excluded and not kept is dropped and logged.

**Why:** a document with no tracked CFR part, not from the CFPB's rule or guidance stream, and with no register keyword in its title or abstract is very unlikely to change a servicing obligation. `dropped.jsonl` is there so misses can be audited, and the eval sample deliberately includes dropped documents so misses are measured.

## Coverage check

`python -m pipeline.prefilter coverage`, enforced by `tests/test_units.py::test_prefilter_coverage_reaches_every_row_and_class`, confirms two things:
- every register row is reachable through a rule-A part in its citation, or a rule-C keyword in its law name, citation or constraint;
- every behavior class in `taxonomy/behaviors.yaml` is reachable through its register rows or a keyword in its own description.

With the keywords added above, all 73 register rows and all 17 behavior classes are reached. The four v1.1 gap rows (FCRA-PERMPURP-001, FCRA-MEDINFO-001, NCUA-INDIRECT-001, STATE-CREDITRPT-001) are reached by rule A (12 CFR 1022) or existing keywords such as "credit reporting", "servicing", "servicer" and "furnisher"; no keyword was added for them. Before the additions, 14 rows were not reached (listed in the table above). No behavior class was unreached.

## Eval manifest (`eval/sample_manifest.csv`)

Decisions for the 30 sampled documents are computed by `classify` from each document's ingested Federal Register metadata. CFR parts are never inferred (see rule A).

Recompute with `python eval/select_sample.py --manifest-only` (reads `data/raw/federal_register.jsonl.gz`; no network). All 30 sampled documents are in the store. Current result: 16 keep (A 10, B 5, C 1) and 14 drop (excluded 7, no_match 7).

## Results on the full ingest (2024-09-23 to 2026-09-24, 2,203 documents)

- Kept 201: A (CFR part) 102, B (CFPB type) 35, C (keyword) 64. The reason is the first rule that matched. Counting every match regardless of order: A 102, B 77, C 107.
- Excluded as administrative 1,052: PRA information collection 772, FCC spectrum/broadcast/licensing 138, Sunshine Act 81, Privacy Act SORN 58, agency organization 3.
- Dropped as `no_match`: 950.
- 36 excluded documents also matched a keep rule. None matched rule A. Two were CFPB Privacy Act notices whose "rescission" is of a records system, not of guidance. The rest were keyword hits in paperwork notices, meeting notices and two FCC satellite and internet rules.

