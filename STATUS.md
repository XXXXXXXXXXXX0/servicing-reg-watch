# Status

Branch: `claude/eloquent-goodall-jas2zw`. v1.2 complete; register pre-check done 2026-09-27.

## Completed
- v1 eval final (TP 5, FP 1, FN 1, TN 23); v1.1 rules; v1.2 steps 1-7 (product lines, segments, 18 rows, prefilter, triage).
- Human review: 12 decisions in REVIEW_LOG.md. 2024-29699 disapproval confirmed 2026-09-27 (P.L. 119-10, S.J.Res. 18, May 9, 2025; text committed); record stays closed, reason updated.
- NCUA-RECORDS-001 added (12 CFR 749, cited only to FR Doc. 2026-12058). Register 92 rows (85 verify, 7 unresearched, 0 verified).
- Pre-check (`pipeline/verify.py`, `register/primary_sources.yaml`): all 85 verify rows have `machine_check`: 63 match, 6 mismatch, 16 not_checkable. Every federal row has `preemption`; state rows have `federal_interaction`. Report: `register/VERIFICATION_REPORT.md`.
- Network 2026-09-27: blocked by policy: docs.fcc.gov, nacha.org, pcisecuritystandards.org, occ.gov, federalreserve.gov, aicpa-cima.com, leg.colorado.gov, le.utah.gov, consumerfinance.gov, congress.gov, tcss.legis.texas.gov (Texas statute text). www.mass.gov answers 403 to automated requests (940 CMR).

## Data files (committed)
- Store: FR metadata (3,683 docs), manifest, eCFR (+46 files dated 2026-09-24), GovInfo (+4 FR docs), new `data/raw/primary/` (59 files: U.S. Code, CA, FL, MA pages; P.L. 119-10). Triage dirs unchanged.

## Open issues
- Mismatches await the reviewer: REGF-STOP-003, REGZ-MOD-001, FCRA-MEDINFO-001, UDAAP-INS-001, CA-ROSENTHAL-001, FL-FCCPA-004. No row wording or status changed except two MA source_url 404 fixes.
- eCFR still shows 12 CFR 1026.62 (and its sentence in 1005.10(e)(1)): an eCFR lag, not evidence the 2024-29699 rule is in force.
- FCRA-MEDINFO-001: eCFR shows the 2024-30824 amendments; whether that rule still stands was not confirmed.
- 11 rows unverifiable here (TX 5, MA 940 CMR 2, CO, UT, FCC 24-17, SR 11-7); Nacha, PCI, SOC 2 proprietary.
- Watch: 2024-29292 (Reg V ANPR), 2026-07960 (FCC onshoring NPRM). NCUA 2026-12058 awaits control-validation sign-off.

## Next step
- Reviewer decisions on the 6 mismatches and blocked sources; then sign-off to set rows verified. State research for thin areas; fresh eval set.
