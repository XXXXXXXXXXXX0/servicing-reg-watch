"""Step 2 - Prefilter: exclusion, CFR-part, CFPB-type and keyword rules
(stated with reasons in PREFILTER.md) applied to already-ingested raw JSON.

Every document gets a decision and a reason. Dropped documents are logged in
full to prefilter/dropped.jsonl so a reviewer can audit what never reached
triage. Nothing is fetched.

    python -m pipeline.prefilter [--data-dir DIR]
    python -m pipeline.prefilter coverage   # register rows / behavior classes each rule reaches
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter

from . import config
from .common import data_paths, write_json, write_jsonl
from .ingest import load_raw_docs

# Rules and the reason for each are stated in PREFILTER.md. Order: EXCLUDE
# (administrative notices) first; then KEEP on rule A (CFR part), B (CFPB
# document type) or C (keyword in title or abstract); DROP everything else.

CFPB = "consumer-financial-protection-bureau"
FCC = "federal-communications-commission"

# EXCLUDE rules, matched against the title: (reason, pattern, doc types it applies to or None).
EXCLUDE = [
    ("excluded_pra_information_collection",
     r"information collection|submission for OMB review|proposed collection; comment request", {"Notice"}),
    ("excluded_sunshine_act_meeting", r"Sunshine Act", None),
    ("excluded_privacy_act_sorn", r"Privacy Act of 1974|system of records", None),
    ("excluded_agency_organization",
     r"delegations? of authority|statement of organization|organization(?:al)?(?: and|,) functions"
     r"|agency organization|rules of organization", None),
]
# FCC spectrum, broadcast and licensing items (FCC documents only). Acronyms case-sensitive.
FCC_LICENSING = [r"spectrum", r"broadcast", r"television", r"radio servic", r"\bFM\b", r"\bAM\b", r"\bLPFM\b",
                 r"licens", r"auction", r"satellite", r"antenna", r"amateur radio", r"table of allotments",
                 r"\bMHz\b", r"\bGHz\b"]
FCC_CASE_SENSITIVE = {r"\bFM\b", r"\bAM\b", r"\bLPFM\b", r"\bMHz\b", r"\bGHz\b"}

# Rule B: CFPB guidance types, matched against title, action and abstract.
CFPB_GUIDANCE = r"interpretive rule|advisory opinion|policy statement|statement of policy|supervisory highlights"
WITHDRAWAL = r"withdraw|rescind|rescission|revocation|revoke"
GUIDANCE_WORDS = r"guidance|interpretive|advisory opinion|policy statement|statement of policy|circular|bulletin|interpretation"

# Rule C keywords, from the rule text. Stems (trailing "*") match any word
# ending; every other term matches as a whole word or phrase, with an optional
# plural "s"/"es" on the last word. Hyphens and spaces are interchangeable.
KEYWORDS = [
    "debt collection", "debt collector", "servicing", "servicer", "delinquen*", "loan modification",
    "deferral", "forbearance", "auto loan", "automobile", "motor vehicle", "vehicle financ*",
    "repossession", "right to cure", "deficiency", "guaranteed asset protection", "GAP waiver",
    "add-on product", "collateral protection insurance", "force-placed", "lien release", "total loss",
    "Telephone Consumer Protection Act", "robocall", "autodialer", "automatic telephone dialing",
    "artificial voice", "prerecorded", "revoke consent", "revocation of consent", "text message",
    "call recording", "recorded call", "validation notice", "electronic signature", "E-SIGN",
    "electronic fund transfer", "preauthorized", "Regulation E", "ACH", "convenience fee", "pay-to-pay",
    "furnisher", "credit reporting", "Regulation V", "Regulation P", "privacy notice", "safeguards",
    "information security", "data breach", "unfair, deceptive, or abusive", "UDAAP",
    "Equal Credit Opportunity", "Regulation B", "servicemember", "bankruptcy", "deceased",
    "cease communication", "third-party relationship", "third-party risk", "service provider",
    "model risk", "artificial intelligence", "chatbot",
]
# Added by the coverage check (PREFILTER.md lists each with the row or class it reaches).
COVERAGE_KEYWORDS = [
    "unfair or deceptive", "collection practices", "recording", "wiretap", "bot", "Nacha",
    "SOC 2", "PCI DSS",
]
# Case-sensitive acronyms. Inside "GAP waiver" only GAP is case-sensitive.
CASE_SENSITIVE = {"ACH", "UDAAP", "GAP waiver", "E-SIGN", "SOC 2", "PCI DSS"}


def _keyword_pattern(term: str) -> re.Pattern:
    stem = term.endswith("*")
    words = re.split(r"[-\s]+", term.rstrip("*"))
    body = r"[-\s]+".join(re.escape(w) for w in words)
    if term == "GAP waiver":
        body = r"GAP[-\s]+(?i:waiver)"
    tail = r"" if stem else r"(?:s|es)?\b"
    flags = 0 if term in CASE_SENSITIVE else re.IGNORECASE
    return re.compile(rf"\b{body}{tail}", flags)


_KEYWORDS = {t: _keyword_pattern(t) for t in KEYWORDS + COVERAGE_KEYWORDS}
_EXCLUDE = [(r, re.compile(p, re.IGNORECASE), types) for r, p, types in EXCLUDE]
_FCC = [re.compile(t, 0 if t in FCC_CASE_SENSITIVE else re.IGNORECASE) for t in FCC_LICENSING]


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


def keyword_hits(text: str) -> list[str]:
    return [t for t, p in _KEYWORDS.items() if p.search(text or "")]


def exclusion(doc: dict) -> str | None:
    title = doc.get("title") or ""
    for reason, pat, types in _EXCLUDE:
        if pat.search(title) and (types is None or doc.get("type") in types):
            return reason
    if FCC in _agency_slugs(doc) and any(p.search(title) for p in _FCC):
        return "excluded_fcc_spectrum_broadcast_licensing"
    return None


def cfpb_type(doc: dict) -> str | None:
    if CFPB not in _agency_slugs(doc):
        return None
    head = " ".join(filter(None, [doc.get("title"), doc.get("action"), doc.get("abstract")]))
    if re.search(WITHDRAWAL, head, re.IGNORECASE) and re.search(GUIDANCE_WORDS, head, re.IGNORECASE):
        return "guidance_withdrawal_or_rescission"
    m = re.search(CFPB_GUIDANCE, head, re.IGNORECASE)
    if m:
        return m.group(0).lower()
    return {"Rule": "final_rule", "Proposed Rule": "proposed_rule"}.get(doc.get("type"))


def classify(doc: dict) -> dict:
    text = " ".join(filter(None, [doc.get("title"), doc.get("abstract")]))
    decision = {"keep": False, "reason": "", "exclude": exclusion(doc), "cfr_hits": _cfr_hits(doc),
                "cfpb_type": cfpb_type(doc), "keyword_hits": keyword_hits(text)}
    if decision["exclude"]:
        decision["reason"] = decision["exclude"]
    elif decision["cfr_hits"]:
        decision.update(keep=True, reason="A_cfr_part")
    elif decision["cfpb_type"]:
        decision.update(keep=True, reason="B_cfpb_type")
    elif decision["keyword_hits"]:
        decision.update(keep=True, reason="C_keyword")
    else:
        decision["reason"] = "no_match"
    return decision


# ------------------------------------------------------------ coverage check
_CITED_PART = re.compile(r"(\d+)\s+CFR\s+(?:parts?\s+)?(\d+)", re.IGNORECASE)


def _row_reach(row: dict) -> list[str]:
    """Rule A parts cited by a register row, and rule C keywords in its law name, citation or constraint."""
    cite = row.get("citation") or ""
    parts = [f"{t} CFR {p}" for t, p in _CITED_PART.findall(cite) if (int(t), p) in config.PREFILTER_CFR_PARTS]
    return parts + keyword_hits(f"{row.get('law') or ''} {cite} {row.get('constraint') or ''}")


def coverage() -> dict:
    """Which rule-A part or rule-C keyword reaches each register row and each
    behavior class. A class is reached through its rows or its own description."""
    from .common import load_register, load_taxonomy
    rows = {r["id"]: _row_reach(r) for r in load_register()}
    classes = {}
    for cls, spec in load_taxonomy()["behavior_classes"].items():
        via_rows = sorted({h for r in load_register() if cls in r.get("behavior_classes", []) for h in rows[r["id"]]})
        classes[cls] = sorted(set(via_rows) | set(keyword_hits(spec.get("description", ""))))
    return {"rows": rows, "classes": classes,
            "unreached_rows": sorted(k for k, v in rows.items() if not v),
            "unreached_classes": sorted(k for k, v in classes.items() if not v)}


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
    ap.add_argument("command", nargs="?", default="run", choices=["run", "coverage"])
    ap.add_argument("--data-dir")
    args = ap.parse_args(argv)
    if args.command == "coverage":
        c = coverage()
        print(f"coverage: {len(c['rows']) - len(c['unreached_rows'])}/{len(c['rows'])} register rows, "
              f"{len(c['classes']) - len(c['unreached_classes'])}/{len(c['classes'])} behavior classes reached")
        for k in c["unreached_rows"] + c["unreached_classes"]:
            print(f"  unreached: {k}")
        return 1 if c["unreached_rows"] or c["unreached_classes"] else 0
    s = run(args.data_dir)
    print(f"prefilter: {s['kept']} kept, {s['dropped']} dropped (logged) of {s['total']}")
    print(f"  kept: {s['kept_reasons']}  dropped: {s['dropped_reasons']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
