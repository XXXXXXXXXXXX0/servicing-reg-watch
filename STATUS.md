# Status

Branch: `claude/eloquent-goodall-jas2zw`. v1.2 complete; register pre-check reviewed; disapproval check added 2026-09-27.

## Completed
- v1 eval final (TP 5, FP 1, FN 1, TN 23); v1.1 rules; v1.2 steps 1-7.
- Pre-check (`pipeline/verify.py`, `register/VERIFICATION_REPORT.md`): 69 machine_verified, 1 verified (MA-940CMR-001), 15 verify, 7 unresearched.
- Records: 2024-30824 and C1-2024-30824 closed by the vacatur (external link); 2024-22962 meta notes its May 12, 2025 withdrawal (FR 2025-08286).
- Congressional disapproval check (`pipeline/cra.py`, pipeline step 1b after ingest): GovInfo PLAW collection, window 2024-09-23..2026-09-24: 305 public laws, 23 CRA disapprovals (all confirmed by "no force or effect" text).
- Matches in the store: P.L. 119-10 -> 2024-29699 (linked in meta; record already closed, signed); P.L. 119-11 -> 2024-27836 (CFPB digital payment apps larger participants; no change record, auto-closed at triage); P.L. 119-19 -> 2024-21560 (OCC bank merger rule; no change record).

## Data files (committed)
- Store: FR metadata (3,683 docs), manifest, eCFR, GovInfo, `data/raw/primary/` (+22 public laws: text `PLAW-*.htm.gz` and `PLAW-*.summary.json.gz`). The PLAW listing is fetched each run, not saved.
- Runtime: `data/cra/disapprovals.json`.

## Open issues
- Court vacaturs remain uncovered by any automated check (2024-30824 was linked by hand).
- The disapproval check reports unlinked matches; linking and closing stay a reviewed step (BUILD_SPEC Section 2).
- eCFR still shows 12 CFR 1026.62 and 1022.30(d) [Reserved]: eCFR lag.
- 15 verify rows not checkable here (TX 5, MA-940CMR-002, CO, UT, SR 11-7; Nacha 3, PCI, SOC 2) plus FCRA-MEDINFO-001 (override).
- Blocked hosts: docs.fcc.gov, nacha.org, pcisecuritystandards.org, occ.gov, federalreserve.gov, aicpa-cima.com, leg.colorado.gov, le.utah.gov, consumerfinance.gov, congress.gov, tcss.legis.texas.gov; www.mass.gov refuses bots.
- Watch: 2024-29292 (Reg V ANPR), 2026-07960 (FCC onshoring NPRM). NCUA 2026-12058 awaits control-validation sign-off.

## Next step
- Decide whether a source for court vacaturs is wanted; hand-check remaining verify rows; state research; fresh eval set.
