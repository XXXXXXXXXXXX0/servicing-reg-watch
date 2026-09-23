"""Draw the stratified eval sample (BUILD_SPEC Section 10) from an ingest run.

    python eval/select_sample.py [--data-dir DIR] [--seed N] [--force]

Writes:
  eval/labels.csv        - doc_id, title, url, and EMPTY label columns for blind labeling
  eval/sample_strata.csv - which stratum each document was drawn from

The labeler should fill in labels.csv before looking at sample_strata.csv or any
triage output. Strata are keyword heuristics for drawing a balanced sample, not
labels. Refuses to overwrite a labels.csv that already has rows unless --force.
"""
from __future__ import annotations

import argparse
import csv
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.common import data_paths, read_jsonl  # noqa: E402
from pipeline.ingest import load_raw_docs  # noqa: E402

LABEL_FIELDS = ["doc_id", "title", "html_url", "label_relevant", "label_behavior_classes",
                "label_tier", "labeled_by", "labeled_on", "notes"]

# (stratum, group, target count, predicate)
def _t(d):
    return " ".join(filter(None, [d.get("title"), d.get("abstract")]))

def _parts(d):
    return {(int(r.get("title") or 0), str(r.get("part"))) for r in d.get("cfr_references") or []}

STRATA = [
    ("reg_f", "positive_candidate", 4, lambda d: (12, "1006") in _parts(d) or re.search(r"debt collect", _t(d), re.I)),
    ("reg_e", "positive_candidate", 4, lambda d: (12, "1005") in _parts(d) or re.search(r"electronic fund transfer", _t(d), re.I)),
    ("tcpa_servicing", "positive_candidate", 4, lambda d: re.search(r"robocall|robotext|revocation|artificial.{0,20}voice", _t(d), re.I)
        and not re.search(r"telemarket|lead generat|one-to-one", _t(d), re.I)),
    ("collections_auto_supervisory", "positive_candidate", 3, lambda d: re.search(
        r"auto(?:mobile)? (?:loan|financ)|motor vehicle|repossess|supervisory highlights|collection", _t(d), re.I)),
    ("mortgage_servicing", "hard_negative", 3, lambda d: (12, "1024") in _parts(d) or re.search(r"mortgage", _t(d), re.I)),
    ("overdraft", "hard_negative", 3, lambda d: re.search(r"overdraft|non-sufficient funds", _t(d), re.I)),
    ("open_banking", "hard_negative", 2, lambda d: (12, "1033") in _parts(d) or re.search(r"personal financial data|open banking", _t(d), re.I)),
    ("tcpa_marketing", "hard_negative", 2, lambda d: re.search(r"telemarket|lead generat|one-to-one", _t(d), re.I)),
    ("other", "easy_negative", 5, lambda d: True),
]


def select(docs, seed=0):
    rng = random.Random(seed)
    taken, rows = set(), []
    for name, group, n, pred in STRATA:
        pool = sorted((d for d in docs if d["document_number"] not in taken and pred(d)),
                      key=lambda d: d["document_number"])
        for d in rng.sample(pool, min(n, len(pool))):
            taken.add(d["document_number"])
            rows.append((name, group, d))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--out-dir", default=str(ROOT / "eval"))
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    labels = out / "labels.csv"
    if labels.exists() and not args.force:
        with open(labels) as f:
            if list(csv.DictReader(f)):
                print("labels.csv already has rows; use --force to replace (this discards labels)")
                return 1
    docs = load_raw_docs(args.data_dir)
    dropped = {r["document_number"] for r in read_jsonl(data_paths(args.data_dir)["prefilter"] / "dropped.jsonl")}
    rows = select(docs, args.seed)
    # Shuffle label order so strata are not inferable from row position.
    order = rows[:]
    random.Random(args.seed + 1).shuffle(order)
    with open(labels, "w", newline="") as f:
        w = csv.DictWriter(f, LABEL_FIELDS)
        w.writeheader()
        for _, _, d in order:
            w.writerow({"doc_id": d["document_number"], "title": d.get("title"), "html_url": d.get("html_url")})
    with open(out / "sample_strata.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["doc_id", "stratum", "group", "dropped_by_prefilter"])
        for name, group, d in rows:
            w.writerow([d["document_number"], name, group, d["document_number"] in dropped])
    counts = {}
    for _, g, _ in rows:
        counts[g] = counts.get(g, 0) + 1
    print(f"sample: {len(rows)} documents {counts} -> {labels}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
