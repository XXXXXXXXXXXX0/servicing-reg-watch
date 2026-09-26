"""Step 5 - Route. Auto-close only if relevant=false AND confidence >= 0.85
(BUILD_SPEC Section 7). Everything else, including documents with missing or
invalid triage output, goes to the human review queue. A document whose full
text could not be fetched goes to human review (full_text_unavailable) whatever
its triage output says: it is not triaged from partial information.

    python -m pipeline.route [--data-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import sys

from .common import data_paths, load_register, read_json, write_json
from .triage import full_text_available, validate_output

AUTO_CLOSE_CONFIDENCE = 0.85


def decide(triage: dict | None, errors: list[str] | None = None,
           has_full_text: bool = True) -> tuple[str, str]:
    if not has_full_text:
        return "review", "full_text_unavailable"
    if triage is None:
        return "review", "untriaged"
    if errors:
        return "review", "invalid_triage_output"
    if triage["relevant"] is False and triage["confidence"] >= AUTO_CLOSE_CONFIDENCE:
        return "auto_closed", "not_relevant_high_confidence"
    if triage["relevant"]:
        return "review", "relevant"
    return "review", "not_relevant_low_confidence"


def run(data_dir=None) -> dict:
    paths = data_paths(data_dir)
    register_ids = {r["id"] for r in load_register()}
    review, closed = [], []
    for packet_path in sorted(paths["triage_inputs"].glob("*.json")):
        if packet_path.name.startswith("_"):
            continue
        doc_id = packet_path.stem
        packet = read_json(packet_path)
        out_path = paths["triage"] / f"{doc_id}.json"
        triage, errors = None, None
        if out_path.exists():
            try:
                triage = json.loads(out_path.read_text())
                errors = validate_output(triage, doc_id, register_ids)
            except json.JSONDecodeError as e:
                triage, errors = {}, [f"invalid JSON: {e}"]
        queue, reason = decide(triage, errors, full_text_available(packet))
        item = {
            "doc_id": doc_id,
            "title": packet["metadata"].get("title"),
            "type": packet["metadata"].get("type"),
            "publication_date": packet["metadata"].get("publication_date"),
            "html_url": packet["metadata"].get("html_url"),
            "route_reason": reason,
            "relevant": (triage or {}).get("relevant"),
            "confidence": (triage or {}).get("confidence"),
            "validation_errors": errors or [],
            "full_text_missing_reason": packet.get("full_text_missing_reason"),
        }
        (closed if queue == "auto_closed" else review).append(item)
    review.sort(key=lambda i: (i["route_reason"] != "relevant", i["publication_date"] or ""))
    write_json(paths["queue"] / "review_queue.json", review)
    write_json(paths["queue"] / "auto_closed.json", closed)
    summary = {"review": len(review), "auto_closed": len(closed),
               "review_by_reason": {r: sum(1 for i in review if i["route_reason"] == r)
                                    for r in sorted({i["route_reason"] for i in review})}}
    write_json(paths["queue"] / "summary.json", summary)
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir")
    args = ap.parse_args(argv)
    print(f"route: {run(args.data_dir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
