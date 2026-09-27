# Status

Branch: `claude/eloquent-goodall-jas2zw`. v1.2 complete; register pre-check reviewed 2026-09-27.

## Completed
- v1 eval final (TP 5, FP 1, FN 1, TN 23); v1.1 rules; v1.2 steps 1-7.
- Pre-check (`pipeline/verify.py`, `register/primary_sources.yaml`, `register/VERIFICATION_REPORT.md`): 85 rows checked; after review 69 match, 1 mismatch (overridden), 15 not_checkable.
- Reviewer decisions 2026-09-27 (REVIEW_LOG.md): five mismatched rows corrected and re-checked (match); FCRA-MEDINFO-001 kept by override (2024-30824 vacated July 11, 2025, Cornerstone v. CFPB); 2024-30824 record closed by an external vacatur link; TCPA-AIVOICE-001 cites FR Doc. 2024-19028; 2024-29699 record file reverted to signed text (confirmation in log and record_meta notes).
- New status `machine_verified`. Register 92 rows: 69 machine_verified, 1 verified (MA-940CMR-001, hand-checked), 15 verify, 7 unresearched.

## Data files (committed)
- Store: FR metadata (3,683 docs), manifest, eCFR (dated 2026-09-24 for the pre-check), GovInfo, `data/raw/primary/` (U.S. Code, CA, FL, MA, P.L. 119-10). No new fetches this session.

## Open issues
- Held for reviewer: note on 2024-22962 that CFPB "revoked the advisory opinion in July 2025". Committed FR Doc. 2025-08286 records its withdrawal as of May 12, 2025 (already linked); no July 2025 revocation is in the store.
- C1-2024-30824 (correction to the vacated rule) is still open; not changed.
- eCFR still shows 12 CFR 1026.62 and 1022.30(d) [Reserved]: eCFR lag.
- 15 verify rows: not checkable here (TX 5, MA-940CMR-002, CO, UT, SR 11-7; Nacha 3, PCI, SOC 2) plus FCRA-MEDINFO-001.
- Blocked hosts: docs.fcc.gov, nacha.org, pcisecuritystandards.org, occ.gov, federalreserve.gov, aicpa-cima.com, leg.colorado.gov, le.utah.gov, consumerfinance.gov, congress.gov, tcss.legis.texas.gov; www.mass.gov refuses bots.
- Watch: 2024-29292 (Reg V ANPR), 2026-07960 (FCC onshoring NPRM). NCUA 2026-12058 awaits control-validation sign-off.

## Next step
- Decide the 2024-22962 note and C1-2024-30824; hand-check the 15 verify rows where possible; state research; fresh eval set.
