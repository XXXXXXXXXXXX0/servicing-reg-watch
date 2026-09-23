"""Step 1 - Ingest: pull Federal Register documents for the tracked agencies,
document types and window; store raw JSON (including the abstract) per document.

    python -m pipeline.ingest [--offline] [--start YYYY-MM-DD --end YYYY-MM-DD]
    python -m pipeline.ingest text [--offline]   # fetch full text for prefilter survivors

Queries are chunked by agency and calendar month. A chunk whose reported count
exceeds what the API will page through is split in half until it fits. The
manifest records reported vs. retrieved counts for every chunk; the command
exits non-zero if any chunk is incomplete.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys

from . import config
from .common import data_paths, read_json, read_jsonl, write_json
from .sources import NotFound, make_client

PER_PAGE = 1000
MAX_RETRIEVABLE = 2000  # conservative cap on results the API will page through


def default_window(today: dt.date | None = None) -> tuple[dt.date, dt.date]:
    today = today or dt.date.today()
    months = config.WINDOW_MONTHS
    y, m = divmod(today.month - 1 - months, 12)
    year, month = today.year + y, m + 1
    day = min(today.day, 28)
    return dt.date(year, month, day), today


def month_chunks(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        nxt = (cur.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
        yield cur, min(end, nxt - dt.timedelta(days=1))
        cur = nxt


def _params(agency, start, end, page):
    return {
        "conditions[agencies][]": [agency],
        "conditions[type][]": list(config.DOC_TYPES),
        "conditions[publication_date][gte]": start.isoformat(),
        "conditions[publication_date][lte]": end.isoformat(),
        "fields[]": config.FR_FIELDS,
        "per_page": PER_PAGE,
        "page": page,
        "order": "oldest",
    }


def fetch_chunk(client, agency, start, end, manifest):
    first = client.get_json(config.FR_API, _params(agency, start, end, 1))
    count = int(first.get("count", 0))
    if count > MAX_RETRIEVABLE and start < end:
        mid = start + (end - start) // 2
        yield from fetch_chunk(client, agency, start, mid, manifest)
        yield from fetch_chunk(client, agency, mid + dt.timedelta(days=1), end, manifest)
        return
    results = list(first.get("results") or [])
    page = 1
    while first.get("total_pages", 1) > page and len(results) < count:
        page += 1
        results.extend(client.get_json(config.FR_API, _params(agency, start, end, page)).get("results") or [])
    manifest.append({
        "agency": agency, "start": start.isoformat(), "end": end.isoformat(),
        "reported_count": count, "retrieved": len(results), "complete": len(results) == count,
    })
    yield from results


def ingest(client, start: dt.date, end: dt.date, data_dir=None) -> dict:
    paths = data_paths(data_dir)
    fetched_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    manifest_chunks: list[dict] = []
    docs: dict[str, dict] = {}
    seen_via: dict[str, set] = {}
    for agency in config.AGENCIES:
        for cs, ce in month_chunks(start, end):
            for doc in fetch_chunk(client, agency, cs, ce, manifest_chunks):
                num = doc["document_number"]
                docs[num] = doc
                seen_via.setdefault(num, set()).add(agency)
    for num, doc in docs.items():
        write_json(paths["raw"] / f"{num}.json", {
            "fetched_at": fetched_at,
            "source": config.FR_API,
            "matched_agency_queries": sorted(seen_via[num]),
            "offline_fixture": bool(getattr(client, "offline", False)),
            "document": doc,
        })
    per_agency = {}
    for c in manifest_chunks:
        a = per_agency.setdefault(c["agency"], {"reported": 0, "retrieved": 0, "chunks": 0, "incomplete_chunks": 0})
        a["reported"] += c["reported_count"]
        a["retrieved"] += c["retrieved"]
        a["chunks"] += 1
        a["incomplete_chunks"] += 0 if c["complete"] else 1
    manifest = {
        "fetched_at": fetched_at,
        "offline_fixture": bool(getattr(client, "offline", False)),
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "agencies": config.AGENCIES,
        "doc_types": list(config.DOC_TYPES),
        "unique_documents": len(docs),
        "per_agency": per_agency,
        "complete": all(c["complete"] for c in manifest_chunks),
        "chunks": manifest_chunks,
    }
    write_json(paths["manifest"], manifest)
    return manifest


def load_raw_docs(data_dir=None) -> list[dict]:
    paths = data_paths(data_dir)
    return [read_json(p)["document"] for p in sorted(paths["raw"].glob("*.json"))]


def fetch_texts(client, data_dir=None) -> dict:
    """Fetch full text for documents that survived the prefilter (triage context)."""
    paths = data_paths(data_dir)
    kept = read_jsonl(paths["prefilter"] / "kept.jsonl")
    got, missing = 0, []
    for row in kept:
        num = row["document_number"]
        out = paths["text"] / f"{num}.txt"
        if out.exists():
            got += 1
            continue
        doc = read_json(paths["raw"] / f"{num}.json")["document"]
        url = doc.get("raw_text_url")
        if not url:
            missing.append(num)
            continue
        try:
            text = client.get_text(url)
        except NotFound:
            missing.append(num)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        got += 1
    return {"fetched_or_cached": got, "missing": missing}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="documents", choices=["documents", "text"])
    ap.add_argument("--offline", action="store_true", help="answer from fixtures/, no network")
    ap.add_argument("--start", type=dt.date.fromisoformat)
    ap.add_argument("--end", type=dt.date.fromisoformat)
    ap.add_argument("--data-dir")
    args = ap.parse_args(argv)
    client = make_client(args.offline)
    if args.command == "text":
        res = fetch_texts(client, args.data_dir)
        print(f"text: {res['fetched_or_cached']} available, {len(res['missing'])} missing")
        return 0
    start, end = default_window()
    start, end = args.start or start, args.end or end
    m = ingest(client, start, end, args.data_dir)
    print(f"ingest {m['window']['start']}..{m['window']['end']}: {m['unique_documents']} unique documents")
    for agency, s in m["per_agency"].items():
        flag = "" if s["incomplete_chunks"] == 0 else f"  INCOMPLETE CHUNKS: {s['incomplete_chunks']}"
        print(f"  {agency}: {s['retrieved']}/{s['reported']}{flag}")
    return 0 if m["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
