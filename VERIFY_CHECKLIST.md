# Register verification checklist

Every register row with `status: verify` (69 of 73 rows), taken from `register/federal.yaml` and `register/states/*.yaml` on 2026-09-26. The 4 `unresearched` rows are not listed: they have no citation to check (see `register/INVENTORY.md`, "Coverage map: state research pending").

Most rows were drafted from working knowledge of the law without the primary text open; the three v1.1 gap rows (FCRA-PERMPURP-001, FCRA-MEDINFO-001, NCUA-INDIRECT-001) were cited from committed Federal Register text, but their statute and eCFR text has not been read. None has been checked against its source.

For each row:
1. Open the source URL and confirm the citation points at the provision the row describes (a citation marked "(verify cite)" is known to be uncertain).
2. Read the provision and confirm the row's `constraint` summary and `effective_date` in the YAML match it.
3. Correct the YAML where they differ, then set `status: verified` and `last_checked: <YYYY-MM-DD>` (the validator rejects `verified` without `last_checked`).
4. Regenerate the inventory: `python -m pipeline.inventory`, and confirm `python -m pipeline.inventory --check` passes.

This file is a snapshot. If rows are added or change status, regenerate it from the YAML rather than editing it by hand.

## `register/federal.yaml` (42 rows)

| Done | ID | Law | Citation | Source URL |
|---|---|---|---|---|
| [ ] | TCPA-CONSENT-001 | Telephone Consumer Protection Act | 47 USC 227(b)(1); 47 CFR 64.1200(a)(1)-(3) | <https://www.ecfr.gov/current/title-47/section-64.1200> |
| [ ] | TCPA-AIVOICE-001 | Telephone Consumer Protection Act | FCC Declaratory Ruling, FCC 24-17, CG Docket No. 23-362 (released Feb. 8, 2024) (verify cite) | <https://docs.fcc.gov/public/attachments/FCC-24-17A1.pdf> |
| [ ] | TCPA-REVOKE-001 | Telephone Consumer Protection Act | 47 CFR 64.1200(a)(10)-(12) (paragraph numbers: verify); FCC 24-24, CG Docket No. 02-278 | <https://www.ecfr.gov/current/title-47/section-64.1200> |
| [ ] | REGF-TIME-001 | FDCPA / Regulation F | 15 USC 1692c(a)(1); 12 CFR 1006.6(b)(1) | <https://www.ecfr.gov/current/title-12/section-1006.6> |
| [ ] | REGF-TIME-002 | FDCPA / Regulation F | 15 USC 1692c(a)(3); 12 CFR 1006.6(b)(3) | <https://www.ecfr.gov/current/title-12/section-1006.6> |
| [ ] | REGF-FREQ-001 | FDCPA / Regulation F | 12 CFR 1006.14(b) | <https://www.ecfr.gov/current/title-12/section-1006.14> |
| [ ] | REGF-MEDIA-001 | FDCPA / Regulation F | 12 CFR 1006.14(h); 12 CFR 1006.6(e) | <https://www.ecfr.gov/current/title-12/section-1006.14> |
| [ ] | REGF-DISC-001 | FDCPA / Regulation F | 15 USC 1692g(a); 12 CFR 1006.34 | <https://www.ecfr.gov/current/title-12/section-1006.34> |
| [ ] | REGF-DISC-002 | FDCPA / Regulation F | 15 USC 1692e(11); 12 CFR 1006.18(e) | <https://www.ecfr.gov/current/title-12/section-1006.18> |
| [ ] | REGF-IDENT-001 | FDCPA / Regulation F | 15 USC 1692b, 1692c(b); 12 CFR 1006.6(d), 1006.10; 12 CFR 1006.2(j) | <https://www.ecfr.gov/current/title-12/section-1006.6> |
| [ ] | REGF-STOP-001 | FDCPA / Regulation F | 15 USC 1692c(c); 12 CFR 1006.6(c) | <https://www.ecfr.gov/current/title-12/section-1006.6> |
| [ ] | REGF-STOP-002 | FDCPA / Regulation F | 15 USC 1692c(a)(2); 12 CFR 1006.6(b)(2) | <https://www.ecfr.gov/current/title-12/section-1006.6> |
| [ ] | REGF-STOP-003 | FDCPA / Regulation F | 15 USC 1692g(b); 12 CFR 1006.38(d) | <https://www.ecfr.gov/current/title-12/section-1006.38> |
| [ ] | REGF-FEES-001 | FDCPA / Regulation F | 15 USC 1692f(1); 12 CFR 1006.22(b) | <https://www.ecfr.gov/current/title-12/section-1006.22> |
| [ ] | UDAAP-001 | Consumer Financial Protection Act (UDAAP) | 12 USC 5531, 5536(a)(1)(B) | <https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title12-section5531&num=0&edition=prelim> |
| [ ] | FTC5-001 | FTC Act Section 5 | 15 USC 45(a) | <https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title15-section45&num=0&edition=prelim> |
| [ ] | REGE-PREAUTH-001 | EFTA / Regulation E | 15 USC 1693e(a); 12 CFR 1005.10(b) | <https://www.ecfr.gov/current/title-12/section-1005.10> |
| [ ] | REGE-PREAUTH-002 | EFTA / Regulation E | 15 USC 1693k; 12 CFR 1005.10(e)(1) | <https://www.ecfr.gov/current/title-12/section-1005.10> |
| [ ] | NACHA-TEL-001 | Nacha Operating Rules (TEL entries) | Nacha Operating Rules, Telephone-Initiated Entries (TEL) | <https://www.nacha.org/rules> |
| [ ] | NACHA-WEB-001 | Nacha Operating Rules (WEB entries) | Nacha Operating Rules, Internet-Initiated/Mobile Entries (WEB) | <https://www.nacha.org/rules> |
| [ ] | NACHA-FRAUD-001 | Nacha Operating Rules (fraud monitoring) | Nacha Operating Rules, 2024 Risk Management amendments (fraud monitoring by non-consumer Originators, ODFIs, and others) (verify) | <https://www.nacha.org/rules> |
| [ ] | BK-STAY-001 | Bankruptcy Code (automatic stay) | 11 USC 362(a) | <https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title11-section362&num=0&edition=prelim> |
| [ ] | BK-DISCH-001 | Bankruptcy Code (discharge injunction) | 11 USC 524(a)(2) | <https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title11-section524&num=0&edition=prelim> |
| [ ] | FCRA-DIRECT-001 | FCRA / Regulation V | 15 USC 1681s-2(a)(8); 12 CFR 1022.43 | <https://www.ecfr.gov/current/title-12/section-1022.43> |
| [ ] | FCRA-ACCURACY-001 | FCRA / Regulation V | 15 USC 1681s-2(a)(1)-(3); 12 CFR 1022.42 | <https://www.ecfr.gov/current/title-12/section-1022.42> |
| [ ] | FCRA-PERMPURP-001 | Fair Credit Reporting Act (FCRA): permissible purpose for users of consumer reports | 15 USC 1681b(a)(3)(A); 15 USC 1681b(f) (as cited in CFPB proposed rule, 89 FR 101402, FR Doc. 2024-28690) | <https://www.federalregister.gov/documents/2024/12/13/2024-28690/protecting-americans-from-harmful-data-broker-practices-regulation-v> |
| [ ] | FCRA-MEDINFO-001 | FCRA / Regulation V: creditor prohibition on obtaining or using medical information | 15 USC 1681b(g)(2); 12 CFR 1022.30 (as quoted and amended in CFPB final rule, 90 FR 3276, FR Doc. 2024-30824) | <https://www.federalregister.gov/documents/2025/01/14/2024-30824/prohibition-on-creditors-and-consumer-reporting-agencies-concerning-medical-information-regulation-v> |
| [ ] | NCUA-INDIRECT-001 | NCUA third-party servicing of indirect vehicle loans (regulatory limits removed) | Former 12 CFR 701.21(h) and 741.203(c), removed by NCUA final rule, 91 FR 50677 (FR Doc. 2026-16029), effective September 8, 2026 | <https://www.federalregister.gov/documents/2026/08/06/2026-16029/third-party-servicing-of-indirect-vehicle-loans> |
| [ ] | REGB-001 | ECOA / Regulation B | 15 USC 1691(a); 12 CFR 1002.4(a); 12 CFR 1002.2(m) | <https://www.ecfr.gov/current/title-12/section-1002.4> |
| [ ] | REGZ-MOD-001 | TILA / Regulation Z | 12 CFR 1026.20(a) | <https://www.ecfr.gov/current/title-12/section-1026.20> |
| [ ] | SCRA-RATE-001 | Servicemembers Civil Relief Act | 50 USC 3937 | <https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title50-section3937&num=0&edition=prelim> |
| [ ] | SCRA-REPO-001 | Servicemembers Civil Relief Act | 50 USC 3952 | <https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title50-section3952&num=0&edition=prelim> |
| [ ] | GLBA-REGP-001 | GLBA / Regulation P | 15 USC 6801-6809; 12 CFR 1016 | <https://www.ecfr.gov/current/title-12/part-1016> |
| [ ] | FTC-SAFE-001 | FTC Safeguards Rule | 16 CFR 314.4 | <https://www.ecfr.gov/current/title-16/section-314.4> |
| [ ] | BANKSEC-GUIDE-001 | Interagency Guidelines Establishing Information Security Standards; NCUA security program | 12 CFR part 30 app. B (OCC); 12 CFR part 364 app. B (FDIC); 12 CFR part 208 app. D-2 (Fed); 12 CFR part 748 & app. A (NCUA) | <https://www.ecfr.gov/current/title-12/part-748> |
| [ ] | BANKSEC-INCIDENT-001 | Computer-Security Incident Notification Rule | 12 CFR part 53 (OCC); 12 CFR part 225 subpart N (Fed); 12 CFR part 304 subpart C (FDIC) | <https://www.ecfr.gov/current/title-12/part-53> |
| [ ] | NCUA-CYBER-001 | NCUA cyber incident notification | 12 CFR 748.1(c) | <https://www.ecfr.gov/current/title-12/section-748.1> |
| [ ] | ESIGN-001 | E-SIGN Act | 15 USC 7001(c) | <https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title15-section7001&num=0&edition=prelim> |
| [ ] | TPRM-001 | Interagency Guidance on Third-Party Relationships: Risk Management | 88 FR 37920 (June 9, 2023) (verify cite) | <https://www.occ.gov/news-issuances/bulletins/2023/bulletin-2023-17.html> |
| [ ] | MRM-001 | Model risk management guidance | Federal Reserve SR 11-7 (Apr. 4, 2011); OCC Bulletin 2011-12 | <https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm> |
| [ ] | SOC2-001 | SOC 2 (AICPA Trust Services Criteria) | AICPA Trust Services Criteria (TSP section 100) | <https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services> |
| [ ] | PCI-001 | PCI DSS | PCI Data Security Standard v4.0.1 | <https://www.pcisecuritystandards.org/document_library/> |

## `register/states/ca.yaml` (7 rows)

| Done | ID | Law | Citation | Source URL |
|---|---|---|---|---|
| [ ] | CA-ROSENTHAL-001 | Rosenthal Fair Debt Collection Practices Act | Cal. Civ. Code 1788.17; 1788.2(c) | <https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=1788.17> |
| [ ] | CA-ROSENTHAL-002 | Rosenthal Fair Debt Collection Practices Act | Cal. Civ. Code 1788.11(d)-(e) | <https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=1788.11> |
| [ ] | CA-ROSENTHAL-003 | Rosenthal Fair Debt Collection Practices Act | Cal. Civ. Code 1788.14(c) | <https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=1788.14> |
| [ ] | CA-REC-001 | California Invasion of Privacy Act (recording) | Cal. Penal Code 632, 632.7 | <https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=PEN&sectionNum=632.7> |
| [ ] | CA-AIDISC-001 | California BOT Disclosure Law | Cal. Bus. & Prof. Code 17940-17943 | <https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=BPC&sectionNum=17941> |
| [ ] | CA-REPO-001 | Rees-Levering Motor Vehicle Sales and Finance Act | Cal. Civ. Code 2983.2, 2983.3 | <https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=2983.2> |
| [ ] | CA-UCC9-001 | UCC Article 9 (California) | Cal. Com. Code 9609, 9611, 9614, 9615 | <https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=COM&sectionNum=9609> |

## `register/states/co.yaml` (1 rows)

| Done | ID | Law | Citation | Source URL |
|---|---|---|---|---|
| [ ] | CO-AIACT-001 | Colorado Artificial Intelligence Act (SB 24-205) | C.R.S. 6-1-1701 et seq.; 6-1-1704 (consumer disclosure) (verify) | <https://leg.colorado.gov/bills/sb24-205> |

## `register/states/fl.yaml` (6 rows)

| Done | ID | Law | Citation | Source URL |
|---|---|---|---|---|
| [ ] | FL-FCCPA-001 | Florida Consumer Collection Practices Act | Fla. Stat. 559.72(17) | <http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0500-0599/0559/Sections/0559.72.html> |
| [ ] | FL-FCCPA-002 | Florida Consumer Collection Practices Act | Fla. Stat. 559.72(7) | <http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0500-0599/0559/Sections/0559.72.html> |
| [ ] | FL-FCCPA-003 | Florida Consumer Collection Practices Act | Fla. Stat. 559.72(18) | <http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0500-0599/0559/Sections/0559.72.html> |
| [ ] | FL-FCCPA-004 | Florida Consumer Collection Practices Act | Fla. Stat. 559.72(5) | <http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0500-0599/0559/Sections/0559.72.html> |
| [ ] | FL-REC-001 | Florida Security of Communications Act | Fla. Stat. 934.03 | <http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0900-0999/0934/Sections/0934.03.html> |
| [ ] | FL-UCC9-001 | UCC Article 9 (Florida) | Fla. Stat. 679.609, 679.611 | <http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0600-0699/0679/Sections/0679.609.html> |

## `register/states/ma.yaml` (6 rows)

| Done | ID | Law | Citation | Source URL |
|---|---|---|---|---|
| [ ] | MA-940CMR-001 | Massachusetts AG Debt Collection Regulations (creditors) | 940 CMR 7.04(1)(f) | <https://www.mass.gov/regulations/940-CMR-700-debt-collection-regulations> |
| [ ] | MA-940CMR-002 | Massachusetts AG Debt Collection Regulations (creditors) | 940 CMR 7.04(1) (paragraph for time-of-day and third-party limits: verify) | <https://www.mass.gov/regulations/940-CMR-700-debt-collection-regulations> |
| [ ] | MA-REC-001 | Massachusetts Wiretap Act | M.G.L. c. 272, § 99 | <https://malegislature.gov/Laws/GeneralLaws/PartIV/TitleI/Chapter272/Section99> |
| [ ] | MA-CURE-001 | Massachusetts Motor Vehicle Retail Installment Sales Act (right to cure) | M.G.L. c. 255B, § 20A | <https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXX/Chapter255B/Section20A> |
| [ ] | MA-DEFICIENCY-001 | Massachusetts Motor Vehicle Retail Installment Sales Act (deficiency) | M.G.L. c. 255B, § 20B | <https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXX/Chapter255B/Section20B> |
| [ ] | MA-UCC9-001 | UCC Article 9 (Massachusetts) | M.G.L. c. 106, §§ 9-609, 9-611 | <https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXV/Chapter106/Article9/Section9-609> |

## `register/states/multistate.yaml` (1 rows)

| Done | ID | Law | Citation | Source URL |
|---|---|---|---|---|
| [ ] | INS-GAP-001 | GAP waiver and add-on product refund laws | CFPB, Supervisory Highlights, Issue 26, Spring 2022, 87 FR 26727 (May 5, 2022), FR Doc. 2022-09690 | <https://www.federalregister.gov/documents/2022/05/05/2022-09690/supervisory-highlights-issue-26-spring-2022> |

## `register/states/tx.yaml` (5 rows)

| Done | ID | Law | Citation | Source URL |
|---|---|---|---|---|
| [ ] | TX-TDCA-001 | Texas Debt Collection Act | Tex. Fin. Code 392.302(4) | <https://statutes.capitol.texas.gov/Docs/FI/htm/FI.392.htm#392.302> |
| [ ] | TX-TDCA-002 | Texas Debt Collection Act | Tex. Fin. Code 392.304(a)(5) | <https://statutes.capitol.texas.gov/Docs/FI/htm/FI.392.htm#392.304> |
| [ ] | TX-TDCA-003 | Texas Debt Collection Act | Tex. Fin. Code 392.304(a)(8), (a)(19) | <https://statutes.capitol.texas.gov/Docs/FI/htm/FI.392.htm#392.304> |
| [ ] | TX-REC-001 | Texas wiretap statute | Tex. Penal Code 16.02 | <https://statutes.capitol.texas.gov/Docs/PE/htm/PE.16.htm#16.02> |
| [ ] | TX-UCC9-001 | UCC Article 9 (Texas) | Tex. Bus. & Com. Code 9.609, 9.611 | <https://statutes.capitol.texas.gov/Docs/BC/htm/BC.9.htm#9.609> |

## `register/states/ut.yaml` (1 rows)

| Done | ID | Law | Citation | Source URL |
|---|---|---|---|---|
| [ ] | UT-AIDISC-001 | Utah Artificial Intelligence Policy Act | Utah Code 13-2-12 (as amended 2025) (verify) | <https://le.utah.gov/xcode/Title13/Chapter2/13-2-S12.html> |
