"""Step 3 - Diff: for final rules amending a tracked CFR part, fetch the
section text before and after the amendment from the eCFR versioner API and
compute a section-level unified diff.

    python -m pipeline.diff [--offline] [--data-dir DIR]

Statuses written per document:
  diffed                  - at least one section diffed
  proposed_no_ecfr_change - proposed rules do not change the CFR
  pending_effective       - effective date is in the future; eCFR has no after-text yet
  effective_date_unknown  - no effective_on in the FR metadata; not guessed
  no_matching_ecfr_version- no eCFR section version dated on the effective date
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import sys
import xml.etree.ElementTree as ET

from . import config
from .common import data_paths, read_json, read_jsonl, write_json
from .sources import NotFound, make_client

BLOCK_TAGS = {"HEAD", "P", "FP", "HD", "EXTRACT", "NOTE", "CITA", "AUTH", "SOURCE"}


def tracked_refs(doc: dict) -> list[dict]:
    out = []
    for ref in doc.get("cfr_references") or []:
        for t in config.ECFR_TRACKED:
            if str(ref.get("title")) == str(t["title"]) and str(ref.get("part")) == t["part"]:
                out.append(t)
    return out


def xml_to_lines(xml_text: str) -> list[str]:
    """Flatten eCFR section XML to one line per paragraph."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return [ln.strip() for ln in xml_text.splitlines() if ln.strip()]
    lines = []
    for el in root.iter():
        if el.tag in BLOCK_TAGS:
            text = " ".join("".join(el.itertext()).split())
            if text:
                lines.append(text)
    if not lines:
        text = " ".join("".join(root.itertext()).split())
        lines = [text] if text else []
    return lines


# eCFR content version types that can be fetched and diffed. Appendices include
# the Official Interpretations (e.g. "Supplement I to Part 1026"), which carry
# most annual threshold adjustments.
DIFFABLE_TYPES = {"section", "appendix"}


def _section_text(client, date: str, title: int, part: str, section: str, kind: str = "section") -> list[str] | None:
    url = f"{config.ECFR_API}/full/{date}/title-{title}.xml"
    try:
        return xml_to_lines(client.get_text(url, {"part": part, kind: section}))
    except NotFound:
        return None


def diff_document(client, doc: dict, today: dt.date | None = None) -> dict | None:
    refs = tracked_refs(doc)
    if not refs:
        return None
    today = today or dt.date.today()
    num = doc["document_number"]
    base = {"document_number": num, "parts": [f"{r['title']} CFR {r['part']}" for r in refs], "sections": []}
    if doc.get("type") != "Rule":
        return {**base, "status": "proposed_no_ecfr_change" if doc.get("type") == "Proposed Rule" else "not_a_rule"}
    eff = doc.get("effective_on")
    if not eff:
        return {**base, "status": "effective_date_unknown"}
    before = (dt.date.fromisoformat(eff) - dt.timedelta(days=1)).isoformat()
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        versions = client.get_json(f"{config.ECFR_API}/versions/title-{ref['title']}.json", {"part": ref["part"]})
        for v in versions.get("content_versions", []):
            kind = v.get("type", "section")
            if kind not in DIFFABLE_TYPES or v.get("amendment_date") != eff:
                continue
            ident = v.get("identifier")
            if ref.get("section") and ident != ref["section"]:
                continue
            key = (kind, ident)
            if key in seen:  # the versions list can repeat an identifier for one date
                continue
            seen.add(key)
            old = _section_text(client, before, ref["title"], ref["part"], ident, kind)
            new = [] if v.get("removed") else _section_text(client, eff, ref["title"], ref["part"], ident, kind)
            old, new = old or [], new or []
            udiff = list(difflib.unified_diff(old, new, f"{ident} @ {before}", f"{ident} @ {eff}", lineterm="", n=1))
            base["sections"].append({
                "section": ident,
                "type": kind,
                "name": v.get("name"),
                "before_date": before,
                "after_date": eff,
                "change": "added" if not old else "removed" if not new else "amended",
                "substantive": v.get("substantive"),
                "lines_added": sum(1 for ln in udiff if ln.startswith("+") and not ln.startswith("+++")),
                "lines_removed": sum(1 for ln in udiff if ln.startswith("-") and not ln.startswith("---")),
                "unified_diff": "\n".join(udiff),
            })
    if base["sections"]:
        status = "diffed"
    elif dt.date.fromisoformat(eff) > today:
        status = "pending_effective"
    else:
        status = "no_matching_ecfr_version"
    return {**base, "status": status}


def run(client, data_dir=None, today=None) -> dict:
    paths = data_paths(data_dir)
    counts: dict[str, int] = {}
    for row in read_jsonl(paths["prefilter"] / "kept.jsonl"):
        doc = read_json(paths["raw"] / f"{row['document_number']}.json")["document"]
        res = diff_document(client, doc, today)
        if res is None:
            continue
        write_json(paths["diffs"] / f"{doc['document_number']}.json", res)
        counts[res["status"]] = counts.get(res["status"], 0) + 1
    write_json(paths["diffs"] / "_summary.json", counts)
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--data-dir")
    args = ap.parse_args(argv)
    print(f"diff: {run(make_client(args.offline), args.data_dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
