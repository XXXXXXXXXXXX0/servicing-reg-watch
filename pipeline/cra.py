"""Legal-status check: congressional disapprovals under the Congressional Review Act
(5 U.S.C. chapter 8), which eCFR does not reflect until the agency publishes a
conforming amendment.

    python -m pipeline.cra [--start YYYY-MM-DD --end YYYY-MM-DD] [--offline]

Runs after ingest (pipeline/run.py step 1b). It lists public laws issued in the
window from the GovInfo API (published/<start>/<end>?collection=PLAW, key from
GOVINFO_API_KEY in the X-Api-Key header), keeps joint resolutions whose title
disapproves a rule, and confirms each from its text ("such rule shall have no force
or effect", the 5 U.S.C. 802(a) wording). Each disapproval is matched to Federal
Register documents in the store by the Federal Register citation in the law's text
or by the rule title it quotes.

Store: each candidate law's text and summary are saved to the committed store
data/raw/primary/govinfo/<packageId>.htm.gz and <packageId>.summary.json.gz and never
refetched. The published listing is requested on each run and not saved: it gains
entries as laws are posted, so a saved copy would hide new ones (as with the eCFR
versions index in sources.EcfrTextCache).

Output: data/cra/disapprovals.json (runtime). Linking a matched change record
(superseded_by, relation disapproval, in records/record_meta.yaml) is a reviewed step:
this check reports matches that are not linked yet and closes nothing itself
(BUILD_SPEC Section 2: nothing auto-closes except by the Section 7 rule).
Court vacaturs are not covered.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

from . import config
from .common import (RECORDS_DIR, data_paths, read_gz_text, read_json, read_jsonl_gz, write_gz_text,
                     write_json)
from .sources import NotFound, TextUnavailable, html_to_text

# Joint resolutions disapproving a rule (5 U.S.C. 802). Excludes other disapprovals,
# e.g. of District of Columbia Council acts.
TITLE_RE = re.compile(r"disapprov\w*\b.*\brule submitted by", re.I | re.S)
FORCE_RE = re.compile(r"shall\s+have\s+no\s+force\s+or\s+effect", re.I)
FR_CITE_RE = re.compile(r"\b(\d{2,3})\s+Fed\.\s*Reg\.\s*(\d{1,6})\b")
QUOTED_RE = re.compile(r"relating\s+to\s+(?:``|\"|“)(.+?)(?:''|\"|”)", re.I | re.S)
UNQUOTED_RE = re.compile(r"relating\s+to\s+(.+?)\.?$", re.I | re.S)  # titles that do not quote the rule
PLAW_RE = re.compile(r"^PLAW-(\d+)publ(\d+)$")


def _norm(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def _store(data_dir, package_id: str, kind: str) -> Path:
    ext = "summary.json.gz" if kind == "summary" else "htm.gz"
    return data_paths(data_dir)["root"] / "raw" / "primary" / "govinfo" / f"{package_id}.{ext}"


def list_public_laws(client, start: dt.date, end: dt.date) -> list[dict]:
    """Public laws issued in [start, end] (GovInfo published endpoint, all pages)."""
    out, page = [], client.get_govinfo(f"published/{start}/{end}",
                                       {"collection": "PLAW", "pageSize": 1000, "offsetMark": "*"})
    while True:
        out += page.get("packages", [])
        nxt = page.get("nextPage")
        if not nxt:
            return out
        if not nxt.startswith(config.GOVINFO_API):  # the key is only ever sent to the API host
            raise ValueError("unexpected nextPage host")
        page = client.get_govinfo(nxt)


def _cached(client, data_dir, package_id: str, kind: str):
    path = _store(data_dir, package_id, kind)
    if not path.exists():
        if kind == "summary":
            write_gz_text(path, json.dumps(client.get_govinfo(f"packages/{package_id}/summary"), sort_keys=True))
        else:
            write_gz_text(path, client.get_govinfo(f"packages/{package_id}/htm", as_json=False))
    text = read_gz_text(path)
    return json.loads(text) if kind == "summary" else text


def parse_law(pkg: dict, summary: dict, text: str) -> dict:
    """Fields of one disapproval from its listing entry, summary and text."""
    m = PLAW_RE.match(pkg["packageId"])
    body = " ".join(html_to_text(text).split())
    stat = next((f"{c['title']} Stat. {c['pages'][0]}" for r in summary.get("references", [])
                 if r.get("collectionCode") == "STATUTE" for c in r.get("contents", []) if c.get("pages")), None)
    quoted = QUOTED_RE.search(pkg["title"]) or QUOTED_RE.search(body) or UNQUOTED_RE.search(pkg["title"])
    return {
        "package_id": pkg["packageId"],
        "public_law": f"P.L. {m.group(1)}-{m.group(2)}" if m else pkg["packageId"],
        "statute": stat,
        "date_issued": pkg.get("dateIssued"),
        "title": pkg["title"],
        "rule_title": " ".join(quoted.group(1).split()).rstrip(".") if quoted else None,
        "fr_citations": sorted({f"{v} FR {p}" for v, p in FR_CITE_RE.findall(body)}),
        "no_force_or_effect": bool(FORCE_RE.search(body)),
    }


def match_documents(law: dict, docs: list[dict]) -> list[dict]:
    """Store documents matching a disapproval by FR citation or by exact (normalized) title."""
    cites, title = set(law["fr_citations"]), _norm(law.get("rule_title"))
    hits = []
    for d in docs:
        by = [b for b, ok in (("fr_citation", d.get("citation") in cites),
                              ("title", bool(title) and _norm(d.get("title")) == title)) if ok]
        if by:
            hits.append({"doc_id": d["document_number"], "title": d.get("title"), "type": d.get("type"),
                         "citation": d.get("citation"), "publication_date": d.get("publication_date"),
                         "matched_by": by})
    return hits


def record_link_status(doc_id: str, public_law: str, meta: dict, records_dir: Path) -> str:
    links = (meta.get(doc_id) or {}).get("superseded_by", [])
    if any(x.get("doc_id") == public_law and x.get("relation") == "disapproval" for x in links):
        return "linked"
    if (records_dir / f"{doc_id}.md").exists():
        return "needs_link"
    return "no_record"


def run(client, data_dir=None, start: dt.date | None = None, end: dt.date | None = None,
        records_dir: Path | None = None) -> dict:
    from .records import load_record_meta
    paths = data_paths(data_dir)
    if start is None or end is None:
        w = read_json(paths["manifest"])["window"]
        start, end = dt.date.fromisoformat(w["start"]), dt.date.fromisoformat(w["end"])
    try:
        laws = list_public_laws(client, start, end)
    except (NotFound, TextUnavailable) as e:
        return {"skipped": f"{type(e).__name__}: {e}"}
    docs = [r["document"] for r in read_jsonl_gz(paths["fr_store"])]
    records_dir = Path(records_dir or RECORDS_DIR)
    meta = load_record_meta(records_dir)
    found = []
    for pkg in laws:
        if pkg.get("docClass") != "PUBLIC" or not TITLE_RE.search(pkg.get("title", "")):
            continue
        law = parse_law(pkg, _cached(client, data_dir, pkg["packageId"], "summary"),
                        _cached(client, data_dir, pkg["packageId"], "htm"))
        law["matches"] = match_documents(law, docs)
        for h in law["matches"]:
            h["record"] = record_link_status(h["doc_id"], law["public_law"], meta, records_dir)
        found.append(law)
    found.sort(key=lambda x: (x["date_issued"] or "", x["package_id"]))
    write_json(paths["root"] / "cra" / "disapprovals.json",
               {"window": {"start": str(start), "end": str(end)}, "public_laws_listed": len(laws), "disapprovals": found})
    return {
        "public_laws_listed": len(laws), "disapprovals": len(found),
        "unconfirmed_text": [x["public_law"] for x in found if not x["no_force_or_effect"]],
        "matched": {x["public_law"]: [h["doc_id"] for h in x["matches"]] for x in found if x["matches"]},
        "needs_link": [f"{h['doc_id']} <- {x['public_law']}" for x in found for h in x["matches"] if h["record"] == "needs_link"],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=dt.date.fromisoformat)
    ap.add_argument("--end", type=dt.date.fromisoformat)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--data-dir")
    args = ap.parse_args(argv)
    from .sources import make_client
    res = run(make_client(args.offline), args.data_dir, args.start, args.end)
    print(json.dumps(res, indent=1))
    return 1 if res.get("needs_link") or res.get("unconfirmed_text") else 0


if __name__ == "__main__":
    sys.exit(main())
