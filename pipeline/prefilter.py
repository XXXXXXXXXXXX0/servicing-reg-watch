"""Step 2 - Prefilter: cheap keyword / CFR-part filter that drops obvious noise.

Every document gets a decision and a reason. Dropped documents are logged in
full to prefilter/dropped.jsonl so a reviewer can audit what never reached
triage. The filter is biased toward keeping: anything ambiguous goes forward.

    python -m pipeline.prefilter [--data-dir DIR]
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter

from . import config
from .common import data_paths, write_json, write_jsonl
from .ingest import load_raw_docs

# Domain terms: a hit keeps the document. Case-insensitive unless noted.
DOMAIN_TERMS = [
    r"debt collect", r"\bcollector", r"FDCPA", r"Regulation F\b", r"Fair Debt",
    r"Telephone Consumer Protection", r"\bTCPA\b", r"robocall", r"robotext", r"autodial",
    r"artificial (?:or prerecorded )?voice", r"prerecorded", r"revoc\w* (?:of )?consent", r"do[- ]not[- ]call",
    r"electronic fund transfer", r"Regulation E\b", r"preauthorized", r"remittance",
    r"servic(?:er|ing)", r"auto(?:mobile)? (?:loan|financ|lend)", r"motor vehicle", r"vehicle financ",
    r"repossess", r"add-on", r"\bGAP\b", r"total loss",
    r"unfair", r"deceptive", r"abusive", r"UDAAP", r"junk fee", r"convenience fee", r"pay-to-pay",
    r"credit report", r"furnish", r"Fair Credit Reporting", r"Regulation V\b",
    r"Equal Credit Opportunity", r"Regulation B\b", r"Truth in Lending", r"Regulation Z\b",
    r"privacy", r"Gramm-Leach", r"Safeguards", r"information security", r"cyber",
    r"incident notification", r"third[- ]party relationship", r"service provider", r"model risk",
    r"artificial intelligence", r"\bAI\b", r"chatbot", r"automated (?:system|decision|call)",
    r"servicemember", r"Servicemembers Civil Relief", r"\bSCRA\b", r"bankruptcy",
    r"consumer financial", r"consumer credit", r"installment", r"supervisory", r"advisory opinion",
    r"interpretive rule", r"policy statement", r"larger participant", r"\bACH\b",
]
CASE_SENSITIVE = {r"\bAI\b", r"\bGAP\b", r"\bACH\b", r"\bTCPA\b", r"\bSCRA\b", r"FDCPA", r"UDAAP"}

WITHDRAWAL_TERMS = [r"withdraw", r"rescind", r"rescission", r"revok", r"repeal"]

# Obvious noise, matched against the title only. Dropped unless a tracked CFR
# part or a domain term also appears.
NOISE_TERMS = [
    r"Formations of, Acquisitions by, and Mergers of", r"Change in Bank Control",
    r"Proposals to Engage in", r"Sunshine Act", r"\bmeeting\b", r"Privacy Act of 1974",
    r"Agency Information Collection", r"Information Collection Being", r"Proposed Collection; Comment",
    r"termination of receivership", r"Radio Broadcasting", r"\bFM\b", r"\bAM\b", r"Television",
    r"Spectrum", r"Auction", r"Satellite", r"Broadband", r"Universal Service", r"E-Rate",
    r"Wireless Telecommunications Bureau", r"Antenna", r"Amateur Radio", r"Hearing Aid",
    r"Early Termination", r"Premerger", r"Order to Show Cause", r"Consent Order.*(?:Merger|Acquisition)",
]


def _compile(terms):
    return [re.compile(t, 0 if t in CASE_SENSITIVE else re.IGNORECASE) for t in terms]


_DOMAIN = _compile(DOMAIN_TERMS)
_WITHDRAW = _compile(WITHDRAWAL_TERMS)
# Noise terms are matched case-sensitively when they are acronyms.
_NOISE = [re.compile(t, 0 if t in {r"\bFM\b", r"\bAM\b"} else re.IGNORECASE) for t in NOISE_TERMS]


def _hits(patterns, text):
    return [p.pattern for p in patterns if p.search(text)]


def _agency_slugs(doc):
    return {a.get("slug") for a in doc.get("agencies", []) if a.get("slug")}


def _cfr_hits(doc):
    hits = []
    for ref in doc.get("cfr_references") or []:
        try:
            key = (int(ref.get("title")), str(ref.get("part")))
        except (TypeError, ValueError):
            continue
        if key in config.PREFILTER_CFR_PARTS:
            hits.append(f"{key[0]} CFR {key[1]}")
    return hits


def classify(doc: dict) -> dict:
    title = doc.get("title") or ""
    text = " ".join(filter(None, [title, doc.get("abstract"), doc.get("action")]))
    agencies = _agency_slugs(doc)
    cfr = _cfr_hits(doc)
    # "Privacy Act of 1974" system-of-records notices are agency-internal; do not
    # let that phrase alone count as a privacy domain hit.
    domain = _hits(_DOMAIN, re.sub(r"Privacy Act of 1974", "", text, flags=re.IGNORECASE))
    withdraw = _hits(_WITHDRAW, text)
    noise = _hits(_NOISE, title)
    decision = {"keep": False, "reason": "", "cfr_hits": cfr, "domain_hits": domain,
                "withdrawal_hits": withdraw, "noise_hits": noise}
    if cfr:
        decision.update(keep=True, reason="tracked_cfr_part")
    elif "consumer-financial-protection-bureau" in agencies and doc.get("type") in ("Rule", "Proposed Rule") and not domain:
        decision.update(keep=True, reason="cfpb_rulemaking")
    elif noise and not domain:
        decision.update(keep=False, reason="noise_title")
    elif domain:
        decision.update(keep=True, reason="domain_terms")
    elif withdraw and agencies & config.FINANCE_AGENCIES:
        decision.update(keep=True, reason="withdrawal_or_rescission")
    else:
        decision.update(keep=False, reason="no_signal")
    return decision


def run(data_dir=None) -> dict:
    paths = data_paths(data_dir)
    kept, dropped = [], []
    for doc in load_raw_docs(data_dir):
        d = classify(doc)
        row = {
            "document_number": doc["document_number"],
            "title": doc.get("title"),
            "type": doc.get("type"),
            "agencies": sorted(_agency_slugs(doc)),
            "publication_date": doc.get("publication_date"),
            "html_url": doc.get("html_url"),
            **d,
        }
        (kept if d["keep"] else dropped).append(row)
    write_jsonl(paths["prefilter"] / "kept.jsonl", kept)
    write_jsonl(paths["prefilter"] / "dropped.jsonl", dropped)
    summary = {
        "total": len(kept) + len(dropped),
        "kept": len(kept),
        "dropped": len(dropped),
        "kept_reasons": dict(Counter(r["reason"] for r in kept)),
        "dropped_reasons": dict(Counter(r["reason"] for r in dropped)),
    }
    write_json(paths["prefilter"] / "summary.json", summary)
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir")
    args = ap.parse_args(argv)
    s = run(args.data_dir)
    print(f"prefilter: {s['kept']} kept, {s['dropped']} dropped (logged) of {s['total']}")
    print(f"  kept: {s['kept_reasons']}  dropped: {s['dropped_reasons']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
