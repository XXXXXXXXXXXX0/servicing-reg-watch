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

The document's `cfr_references` include one of these parts:
- 12 CFR 1002 (Reg B), 1005 (Reg E), 1006 (Reg F), 1016 (Reg P), 1022 (Reg V), 1026 (Reg Z)
- 47 CFR 64 (TCPA rules are in 64.1200)
- 16 CFR 314 (FTC Safeguards Rule)
- 12 CFR 30 (OCC), 208 (Fed), 225 (Fed), 364 (FDIC), 748 (NCUA): bank and credit union information-security standards, security programs and incident notification

**Why:** these are the parts that hold the register's federal rules. A document that amends one of them changes rule text that a servicing agent follows. It is kept whatever its title says.

**Change from before:** 12 CFR 53 (OCC incident notification), 304 (FDIC incident notification) and 1090 (CFPB larger participants) are no longer on the list. For the incident-notification rule, 12 CFR 225 still reaches the register row (BANKSEC-INCIDENT-001). A CFPB larger-participant rule is still kept by rule B.

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

With the keywords added above, all 69 register rows and all 17 behavior classes are reached. Before the additions, 14 rows were not reached (listed in the table above). No behavior class was unreached.

## Eval manifest (`eval/sample_manifest.csv`)

The prefilter decisions for the 30 sampled documents were recomputed under these rules without fetching anything. The raw ingest JSON from the live run is not in the repository (`data/` is gitignored and the CI live job has not run), so each document's inputs were rebuilt from committed files:
- title, agencies and abstract come from `eval/candidates.md`;
- the document type comes from the pre-cleanup `records/REVIEW_QUEUE.md` (commit 2c06df3), which listed every document the old prefilter kept.

Two inputs could not be rebuilt directly:
- **CFR references.** The old manifest recorded only "tracked_cfr_part", not which part. For the three non-CFPB documents with that reason (2026-06864 and 2026-07960 from the FCC, 2025-22490 from NCUA), the part was inferred from the agency. The FCC codifies only in title 47, and 47 CFR 64 was the old list's only title-47 part. NCUA's only part on the old list was 12 CFR 748. Both parts are in rule A, so the three documents stay kept. The CFPB documents with that reason are kept by rule B regardless.
- **Type and `action` for old drops.** These documents were not in the old queue, so their type is unknown. All of them are still dropped. A few PRA-style titles show `no_match` rather than `excluded_pra_information_collection`, because that exclusion requires type Notice. The decision is the same either way.

Result: 16 keep and 14 drop (previously 18 and 12). Two documents changed from keep to drop: 2025-01142 (CFPB) and 2024-27458 (FTC), both PRA information-collection notices. The full ingested corpus has not been re-run under these rules in this environment. The next `python -m pipeline.prefilter` on live data will do that.
