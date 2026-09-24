# BUILD_SPEC: servicing-reg-watch (v1)

Regulatory change-management pipeline for AI loan-servicing agents in US consumer lending.
Built without access to any production system. Not legal advice.

## 1. Purpose
Detect regulatory changes relevant to AI agents that service consumer loans (contact borrowers, take payments, handle disputes, claims, and recovery), classify their impact on agent behavior, and produce audit-ready change records for human approval.

## 2. Boundaries
- No assumptions about any vendor's internal agents, scripts, or configs. Impact maps to **behavior classes** (Section 5), never to named internal workflows.
- The deployment adapter (Section 9) ships as an empty, documented interface.
- AI narrows the queue; humans approve. Nothing auto-closes unless the rule in Section 7 allows it.
- Every register row cites a primary source, except rows marked `unresearched`. State rows and any row marked `verify` carry that status until checked against primary text.
- `unresearched` rows record a known coverage gap where no primary source has been identified yet. They carry `citation: null` and `source_url: null`; citations are never invented to fill them. They are listed in INVENTORY.md under "Coverage map: state research pending".

## 3. Sources
**Federal Register API** (`https://www.federalregister.gov/api/v1/documents.json`), last 24 months, document types RULE, PRORULE, NOTICE. Agency slugs:
consumer-financial-protection-bureau, federal-communications-commission, federal-trade-commission, comptroller-of-the-currency, federal-deposit-insurance-corporation, federal-reserve-system, national-credit-union-administration.
Withdrawals and rescissions of guidance are changes and must be captured.

**eCFR versioner API** (`https://www.ecfr.gov/api/versioner/v1/`) for point-in-time rule text and diffs:
12 CFR 1005 (Reg E), 1002 (Reg B), 1006 (Reg F), 1016 (Reg P), 1022 (Reg V), 1026 (Reg Z); 47 CFR 64.1200 (TCPA rules); 16 CFR 314 (FTC Safeguards).

**GovInfo** for Federal Register full text (federalregister.gov text URLs redirect to a bot wall): API granule `https://api.govinfo.gov/packages/FR-<publication_date>/granules/<document_number>/htm` with the key from env `GOVINFO_API_KEY` in the `X-Api-Key` header; fallback `https://www.govinfo.gov/content/pkg/FR-<publication_date>/html/<document_number>.htm`. HTML tags are stripped; every response is cached to disk and never refetched.

**Manual rows** (no Federal Register feed): state law, Nacha Operating Rules, bank supervisory bulletins, industry standards.

## 4. Register row schema
```yaml
id: REGF-FREQ-001
law: "FDCPA / Regulation F"
citation: "12 CFR 1006.14(b)"     # null only when status: unresearched
source_url: "<primary source>"  # null only when status: unresearched
agency: CFPB
jurisdiction: federal            # or US-CA, US-FL, US-MA, US-TX; or multi-state (not yet split per state)
applies_to: [third_party_collectors, post_default_servicers]   # who is covered
tier: 1                          # 1 = modeled + evaluated; 2 = inventoried + monitored
behavior_classes: [CONTACT.FREQUENCY]
constraint: "Presumed violation if >7 call attempts in 7 days, or a call within 7 days after a phone conversation, about a particular debt."
change_source: federal_register  # or ecfr | manual
provenance: salient_stated       # salient_stated | third_party_stated | added_by_analysis
provenance_url: "<page where stated, if any>"
status: verify                   # verify | verified | unresearched (no primary source identified yet)
effective_date: 2021-11-30
last_checked: YYYY-MM-DD
```

## 5. Behavior taxonomy (reference model)
Derived from the regulations and public product descriptions. Not any vendor's internal taxonomy.
- CONTACT.TIMING — time and place of contact
- CONTACT.FREQUENCY — attempt and conversation caps
- CONTACT.CONSENT — consent and revocation for automated or artificial-voice calls and texts; channel opt-outs
- CONTACT.RECORDING — call-recording consent and disclosure
- CONTACT.AI_DISCLOSURE — disclosure that the caller is an AI
- DISCLOSURE.REQUIRED — mandated statements (e.g., collector identification, validation information)
- IDENTITY.RIGHT_PARTY — verification before discussing the debt; third-party contact limits
- STOP.TRIGGERS — cease requests, attorney representation, bankruptcy, disputes, deceased borrower, servicemember status
- PAYMENT.AUTHORIZATION — ACH and recurring payment authorization and records
- PAYMENT.FEES — convenience / pay-to-pay fees
- NEGOTIATION.TREATMENT — settlements, extensions, deferrals; fair and non-deceptive treatment
- ACCOUNT.MODIFICATION — modifications that trigger new disclosure duties
- DISPUTES.CREDIT_REPORTING — furnisher accuracy and direct disputes
- DATA.PRIVACY_SECURITY — privacy notices, safeguards, breach duties
- RECOVERY.REPOSSESSION — repossession, right-to-cure, disposition notices, deficiency
- INSURANCE.CLAIMS — total loss, GAP, appraisal-clause deadlines, lien release, collateral protection insurance, add-on refunds
- VENDOR.GOVERNANCE — how bank and credit union customers examine an AI vendor

## 6. Inventory
Provenance key: **S** = named on Salient's public pages; **T** = named in a third-party description of Salient; **A** = added by analysis.

### Tier 1 (modeled, triaged, evaluated)
| Law | Citation | Agency | Behavior classes | Change source | Prov |
|---|---|---|---|---|---|
| TCPA | 47 USC 227; 47 CFR 64.1200; FCC 2024 declaratory ruling on AI-generated voice (verify cite) | FCC | CONTACT.CONSENT | FR + eCFR | S |
| FDCPA / Reg F | 15 USC 1692 et seq.; 12 CFR 1006 | CFPB | CONTACT.TIMING, CONTACT.FREQUENCY, DISCLOSURE.REQUIRED, IDENTITY.RIGHT_PARTY, STOP.TRIGGERS, PAYMENT.FEES | FR + eCFR | S |
| UDAAP | 12 USC 5531, 5536 | CFPB | NEGOTIATION.TREATMENT, all conduct | FR | S |
| FTC Act §5 (nonbanks) | 15 USC 45 | FTC | NEGOTIATION.TREATMENT, all conduct | FR | S (FTC named as regulator) |
| EFTA / Reg E | 15 USC 1693; 12 CFR 1005.10(b) | CFPB | PAYMENT.AUTHORIZATION | FR + eCFR | A |
| Nacha Operating Rules (TEL/WEB entries) | Nacha rulebook | Nacha | PAYMENT.AUTHORIZATION | manual | A |
| Bankruptcy automatic stay | 11 USC 362 | statute | STOP.TRIGGERS | manual | A |
| State collection law (see 6.3) | — | state | CONTACT.*, STOP.TRIGGERS | manual | S ("state rules") |
| State call-recording consent (see 6.3) | — | state | CONTACT.RECORDING | manual | A |

### Tier 2 (inventoried and monitored)
| Law | Citation | Agency | Behavior classes | Change source | Prov |
|---|---|---|---|---|---|
| FCRA / Reg V | 15 USC 1681s-2; 12 CFR 1022.43 | CFPB | DISPUTES.CREDIT_REPORTING | FR + eCFR | T |
| ECOA / Reg B | 12 CFR 1002 | CFPB | NEGOTIATION.TREATMENT | FR + eCFR | A |
| TILA / Reg Z | 12 CFR 1026.20(a) | CFPB | ACCOUNT.MODIFICATION | FR + eCFR | A |
| SCRA | 50 USC 3901 et seq. | statute (DOJ) | STOP.TRIGGERS, RECOVERY.REPOSSESSION | manual | A |
| GLBA / Reg P | 15 USC 6801; 12 CFR 1016 | CFPB | DATA.PRIVACY_SECURITY | FR + eCFR | A |
| FTC Safeguards Rule | 16 CFR 314 | FTC | DATA.PRIVACY_SECURITY | FR + eCFR | A |
| Bank / CU security guidelines | Interagency Guidelines; 12 CFR 748 | OCC, FDIC, Fed, NCUA | DATA.PRIVACY_SECURITY | FR | A |
| E-SIGN | 15 USC 7001 | statute | DISCLOSURE.REQUIRED | manual | A |
| UCC Article 9 (state-adopted) | 9-609, 9-611, 9-614, 9-615 | state | RECOVERY.REPOSSESSION | manual | S ("state repo laws") |
| Right-to-cure notice laws | varies by state | state | RECOVERY.REPOSSESSION | manual | S |
| Deficiency balance rules | varies by state | state | RECOVERY.REPOSSESSION | manual | S |
| GAP waiver / add-on refund laws | varies by state | state | INSURANCE.CLAIMS | manual | S (GAP claims) |
| Appraisal-clause deadlines (total-loss valuation disputes) | policy terms + state insurance law | state | INSURANCE.CLAIMS | manual | S |
| Lien release timing laws | varies by state | state | INSURANCE.CLAIMS | manual | S (lien release) |
| Collateral protection insurance rules | varies by state | state | INSURANCE.CLAIMS | manual | A |
| Interagency Guidance on Third-Party Relationships (2023) | verify FR cite | OCC, FDIC, Fed | VENDOR.GOVERNANCE | FR | A |
| Model risk management | SR 11-7; OCC Bulletin 2011-12 | Fed, OCC | VENDOR.GOVERNANCE | manual | A |
| SOC 2; PCI DSS | AICPA TSC; PCI SSC | industry | VENDOR.GOVERNANCE | manual | T |
| AI disclosure laws | Cal. Bus. & Prof. Code 17940-17943; Utah AI Policy Act; Colorado SB 24-205 (status in flux) | state | CONTACT.AI_DISCLOSURE | manual | A |

### 6.3 State layer (v1: CA, FL, MA, TX; schema scales to all states)
Selection criteria: law reaches lenders collecting their own debts; stricter than federal on a modeled behavior; large auto lending volume. All rows `status: verify`.
| State | Collection law | Reaches first-party lenders | Recording consent |
|---|---|---|---|
| CA | Rosenthal Act, Cal. Civ. Code 1788 et seq. (1788.17 incorporates FDCPA) | Yes | All-party (Penal Code 632, 632.7) |
| FL | Consumer Collection Practices Act, Fla. Stat. 559.55-559.785 | Yes ("any person") | All-party (Fla. Stat. 934.03) |
| MA | 940 CMR 7.00 (7.04 call limits) | Yes | All-party (M.G.L. c. 272 §99) |
| TX | Texas Debt Collection Act, Tex. Fin. Code ch. 392 | Yes | One-party (Tex. Penal Code 16.02) |

## 7. Pipeline
1. **Ingest**: pull Federal Register documents for the agencies and window above; store raw JSON + abstract.
2. **Prefilter**: exclude administrative notices, then keep on CFR part (A), CFPB document type (B) or keyword in title/abstract (C); drop the rest and log everything dropped. Rules and reasons: [PREFILTER.md](PREFILTER.md).
3. **Diff**: for documents amending a tracked CFR part, fetch before/after text from eCFR and compute the section-level diff.
4. **Triage (LLM)**: model from env `MODEL` (default `claude-sonnet-5`), key from env `ANTHROPIC_API_KEY`. Output must validate against:
```json
{
  "doc_id": "", "relevant": true, "confidence": 0.0,
  "change_type": "final_rule|proposed_rule|guidance|withdrawal|enforcement_signal|other",
  "effective_date": null,
  "affected_register_rows": [], "behavior_classes": [],
  "what_changed": "", "compliant_agent_must_now": "",
  "open_questions_for_deploying_team": [], "rationale": ""
}
```
5. **Route**: auto-close only if `relevant=false` and `confidence >= 0.85`. Everything else goes to the human review queue.
6. **Change record**: one markdown file per relevant document (Section 8).

## 8. Change record template
- Document, agency, citation, publication date, effective date, change type
- What changed (diff excerpt where available)
- Affected register rows and behavior classes
- What a compliant agent must now do
- Questions the deploying team must answer: owning config/script, approver, rollout sequence, test evidence required
- Triage confidence and reviewer sign-off field

## 9. Deployment adapter (empty interface)
`adapter/deployment_map.template.yaml`: maps each behavior class to `owning_system`, `config_ref`, `test_suite_ref`, `approver_role`. Shipped unfilled with instructions.

## 10. Eval protocol
- ~30 Federal Register documents, stratified: ~15 relevant (Reg F, Reg E, TCPA servicing-related, collections and auto-servicing supervisory material) and ~15 not relevant, including hard negatives (e.g., mortgage servicing rules, overdraft rules, open banking, marketing-only TCPA consent rules).
- Angela labels **blind**, before seeing any triage output: relevant Y/N, behavior classes, tier.
- Report precision, recall, and behavior-class agreement. State sample size plainly; at n≈15 positives, a perfect recall score supports roughly "above ~80%," not "100%."
- `eval/labels.csv`, `eval/run_eval.py`, `eval/results.md`.

## 11. Repo layout
```
register/federal.yaml  register/states/{ca,fl,ma,tx}.yaml  register/INVENTORY.md (generated)
taxonomy/behaviors.yaml
adapter/deployment_map.template.yaml
pipeline/{ingest,prefilter,diff,triage,route,records}.py
fixtures/            # saved sample documents for offline tests
records/             # generated change records
eval/{labels.csv,run_eval.py,results.md}
.github/workflows/run.yml   .devcontainer/devcontainer.json
README.md
```

## 12. README outline (written as a memo)
Problem; design decisions; what is deliberately not automated and why; eval results with sample-size caveat; provenance method; known limits and deferred depth (Tier 2); how the adapter plugs into a real deployment.

## 13. Acceptance criteria
- Offline run passes against fixtures with no network.
- Live run ingests all listed agencies for the window and produces triage JSON that validates.
- Every register row has citation, source_url, provenance, status (citation and source_url are null only for `unresearched` rows).
- INVENTORY.md regenerates from YAML.
- Eval script produces results.md from labels.csv.
- No secrets in the repo.
