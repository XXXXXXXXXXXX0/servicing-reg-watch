"""Draw the ~30-document eval sample (BUILD_SPEC Section 10) independently of the pipeline.

    python eval/select_sample.py [--offline] [--seed N] [--force] [--start D --end D]
    python eval/select_sample.py --manifest-only   # recompute prefilter decisions, no network

Candidates come from direct Federal Register term searches (full-text search on
the FR side), not from the pipeline's prefilter. The search uses the same
agencies, document types and 24-month window as ingest, so every sampled
document is one the pipeline also processed and run_eval.py can score it.

Queries and how many documents each contributes:
  - the five topic terms for Section 10's relevant-topic side, 3 each (15):
    "Regulation F", "debt collection", "electronic fund transfer", "robocall", "auto loan"
  - Section 10's named hard-negative topics (11):
    "mortgage servicing" 3, "overdraft" 3, "personal financial data rights" 2, "telemarketing" 3
  - an unfiltered draw from the whole window (4)

The query that surfaced a document says nothing about whether it is relevant;
only the blind labeler decides that.

The sample must contain at least MIN_PREFILTER_DROPPED documents that the
prefilter drops (checked with pipeline.prefilter.classify on each candidate),
so the eval measures prefilter misses. If the random draw has fewer, picks are
swapped for dropped candidates from the same query until it does.

Writes:
  eval/labels.csv          - doc_id, title, url, and EMPTY label columns, shuffled
  eval/candidates.md       - number, title, agency, date, abstract, link; nothing else
  eval/sample_manifest.csv - query and prefilter decision per document. Selection
                             bookkeeping only; do not open it before labeling.

Refuses to overwrite a labels.csv that already has rows unless --force.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import config  # noqa: E402
from pipeline.common import data_paths, read_gz_text, read_jsonl_gz, write_gz_text  # noqa: E402
from pipeline.ingest import default_window  # noqa: E402
from pipeline.prefilter import classify  # noqa: E402
from pipeline.sources import make_client  # noqa: E402

LABEL_FIELDS = ["doc_id", "title", "html_url", "label_relevant", "label_behavior_classes",
                "label_tier", "labeled_by", "labeled_on", "notes"]

# (FR search term or None for an unfiltered draw, documents to draw)
QUERIES = [
    ("Regulation F", 3),
    ("debt collection", 3),
    ("electronic fund transfer", 3),
    ("robocall", 3),
    ("auto loan", 3),
    ("mortgage servicing", 3),
    ("overdraft", 3),
    ("personal financial data rights", 2),
    ("telemarketing", 3),
    (None, 4),
]
MIN_PREFILTER_DROPPED = 5
SEARCH_FIELDS = ["document_number", "title", "type", "abstract", "action", "agencies",
                 "cfr_references", "publication_date", "html_url"]
PER_PAGE = 1000


def search(client, term: str | None, start: dt.date, end: dt.date, data_dir=None) -> list[dict]:
    """All documents matching `term` (exact phrase) in the window, agencies and types.
    Results are saved to data/raw/fr_search/ and reused; the API is queried only
    for a term and window not saved yet."""
    import json
    safe = (term or "unfiltered").replace(" ", "_")
    cache = data_paths(data_dir)["fr_search"] / f"{safe}_{start}_{end}.json.gz"
    if cache.exists() and not getattr(client, "offline", False):
        return json.loads(read_gz_text(cache))
    params = {
        "conditions[agencies][]": config.AGENCIES,
        "conditions[type][]": list(config.DOC_TYPES),
        "conditions[publication_date][gte]": start.isoformat(),
        "conditions[publication_date][lte]": end.isoformat(),
        "fields[]": SEARCH_FIELDS,
        "per_page": PER_PAGE,
        "order": "oldest",
    }
    if term:
        params["conditions[term]"] = f'"{term}"'
    out, page = [], 1
    while True:
        res = client.get_json(config.FR_API, {**params, "page": page})
        out.extend(res.get("results") or [])
        if page >= int(res.get("total_pages") or 1):
            if not getattr(client, "offline", False):
                write_gz_text(cache, json.dumps(out, sort_keys=True))
            return out
        page += 1


def select(pools: dict, seed: int = 0) -> tuple[list[tuple[str, dict]], list[str]]:
    """Draw the quota from each pool without repeats, then swap in prefilter-dropped
    documents (same query) until at least MIN_PREFILTER_DROPPED are included."""
    rng = random.Random(seed)
    taken: set[str] = set()
    picks: list[tuple[str, dict]] = []
    for term, n in QUERIES:
        pool = [d for d in pools[term] if d["document_number"] not in taken]
        for d in rng.sample(pool, min(n, len(pool))):
            taken.add(d["document_number"])
            picks.append((term, d))
    warnings = [f"query {t!r}: only {sum(1 for q, _ in picks if q == t)} of {n} available"
                for t, n in QUERIES if sum(1 for q, _ in picks if q == t) < n]

    def dropped(d):
        return not classify(d)["keep"]

    need = MIN_PREFILTER_DROPPED - sum(dropped(d) for _, d in picks)
    order = list(range(len(picks)))
    rng.shuffle(order)
    for i in order:
        if need <= 0:
            break
        term, d = picks[i]
        if dropped(d):
            continue
        spare = [x for x in pools[term] if x["document_number"] not in taken and dropped(x)]
        if not spare:
            continue
        new = rng.choice(spare)
        taken.discard(d["document_number"])
        taken.add(new["document_number"])
        picks[i] = (term, new)
        need -= 1
    if need > 0:
        warnings.append(f"only {MIN_PREFILTER_DROPPED - need} prefilter-dropped documents available")
    return picks, warnings


def _agencies(d: dict) -> str:
    return "; ".join(a.get("name") or a.get("raw_name") or "" for a in d.get("agencies") or [])


def _md(v) -> str:
    return " ".join(str(v or "").split())


def render_candidates(docs: list[dict], start: dt.date, end: dt.date) -> str:
    out = ["# Eval candidates", "",
           f"{len(docs)} Federal Register documents published {start}..{end}, in label order "
           "(same order as `labels.csv`). Label them blind in `labels.csv`.", ""]
    for i, d in enumerate(docs, 1):
        out += [f"## {i}. {_md(d.get('title'))}", "",
                f"- Number: {d['document_number']}",
                f"- Agency: {_agencies(d)}",
                f"- Date: {d.get('publication_date')}",
                f"- Link: {d.get('html_url')}", "",
                f"{_md(d.get('abstract')) or '(no abstract)'}", ""]
    return "\n".join(out)


def refresh_manifest(out: Path, data_dir=None) -> int:
    """Re-run classify() on each sampled document's ingested metadata."""
    store = {r["document"]["document_number"]: r["document"]
             for r in read_jsonl_gz(data_paths(data_dir)["fr_store"])}
    path = out / "sample_manifest.csv"
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    missing = [r["doc_id"] for r in rows if r["doc_id"] not in store]
    if missing:
        print(f"not in the Federal Register store: {missing}; run ingest for the sample window first")
        return 1
    for r in rows:
        c = classify(store[r["doc_id"]])
        r["prefilter_decision"], r["prefilter_reason"] = ("keep" if c["keep"] else "drop"), c["reason"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    n_drop = sum(r["prefilter_decision"] == "drop" for r in rows)
    print(f"manifest: {len(rows)} documents, {len(rows) - n_drop} keep, {n_drop} drop -> {path}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="search fixtures/ instead of the live API")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--start", type=dt.date.fromisoformat)
    ap.add_argument("--end", type=dt.date.fromisoformat)
    ap.add_argument("--out-dir", default=str(ROOT / "eval"))
    ap.add_argument("--data-dir")
    ap.add_argument("--manifest-only", action="store_true",
                    help="recompute prefilter decisions in sample_manifest.csv from the committed "
                         "Federal Register store; no network, labels and candidates untouched")
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    if args.manifest_only:
        return refresh_manifest(out, args.data_dir)
    labels = out / "labels.csv"
    if labels.exists() and not args.force:
        with open(labels) as f:
            if list(csv.DictReader(f)):
                print("labels.csv already has rows; use --force to replace (this discards labels)")
                return 1
    start, end = default_window()
    start, end = args.start or start, args.end or end
    client = make_client(args.offline)
    pools = {term: search(client, term, start, end, args.data_dir) for term, _ in QUERIES}
    picks, warnings = select(pools, args.seed)
    # Shuffle label order so the query is not inferable from row position.
    order = [d for _, d in picks]
    random.Random(args.seed + 1).shuffle(order)
    out.mkdir(parents=True, exist_ok=True)
    with open(labels, "w", newline="") as f:
        w = csv.DictWriter(f, LABEL_FIELDS)
        w.writeheader()
        for d in order:
            w.writerow({"doc_id": d["document_number"], "title": d.get("title"), "html_url": d.get("html_url")})
    (out / "candidates.md").write_text(render_candidates(order, start, end) + "\n")
    with open(out / "sample_manifest.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["doc_id", "search_query", "prefilter_decision", "prefilter_reason"])
        for term, d in picks:
            c = classify(d)
            w.writerow([d["document_number"], term or "(unfiltered)", "keep" if c["keep"] else "drop", c["reason"]])
    n_dropped = sum(not classify(d)["keep"] for _, d in picks)
    print(f"sample: {len(picks)} documents ({n_dropped} dropped by prefilter) from "
          + ", ".join(f"{t or 'unfiltered'}={len(pools[t])}" for t, _ in QUERIES) + f" -> {labels}")
    for w_ in warnings:
        print(f"  warning: {w_}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
