"""Run the pipeline end to end.

    python -m pipeline.run --offline [--data-dir DIR] [--records-dir DIR] [--with-fixture-triage]
    python -m pipeline.run [--triage api|none]           # live

Steps: ingest -> prefilter -> fetch text for survivors -> diff -> triage inputs
-> [triage] -> validate -> route -> records.

Offline mode answers every request from fixtures/ with a fixed window and
"today". `--with-fixture-triage` copies the synthetic triage outputs from
fixtures/triage so route and records run end to end. In live mode, triage is
not run unless `--triage api` is given; untriaged documents route to human review.
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

from . import diff, ingest, prefilter, records, route, triage
from .common import FIXTURES_DIR, data_paths, read_json
from .sources import make_client


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--data-dir")
    ap.add_argument("--records-dir")
    ap.add_argument("--triage", choices=["none", "api"], default="none")
    ap.add_argument("--with-fixture-triage", action="store_true")
    ap.add_argument("--start", type=dt.date.fromisoformat)
    ap.add_argument("--end", type=dt.date.fromisoformat)
    args = ap.parse_args(argv)

    client = make_client(args.offline)
    today = None
    if args.offline:
        w = read_json(FIXTURES_DIR / "federal_register" / "window.json")
        start, end = dt.date.fromisoformat(w["start"]), dt.date.fromisoformat(w["end"])
        today = dt.date.fromisoformat(w["today"])
    else:
        start, end = ingest.default_window()
    start, end = args.start or start, args.end or end
    paths = data_paths(args.data_dir)

    m = ingest.ingest(client, start, end, args.data_dir)
    print(f"[1 ingest] {m['unique_documents']} documents, {start}..{end}, complete={m['complete']}")
    s = prefilter.run(args.data_dir)
    print(f"[2 prefilter] kept {s['kept']}, dropped {s['dropped']} (logged)")
    t = ingest.fetch_texts(client, args.data_dir)
    print(f"[2b text] {t['fetched_or_cached']} available, {t['missing']} missing {t['missing_by_reason']}")
    print(f"[3 diff] {diff.run(client, args.data_dir, today)}")
    print(f"[4 triage inputs] {triage.build_inputs(args.data_dir)} packets")
    if args.with_fixture_triage:
        paths["triage"].mkdir(parents=True, exist_ok=True)
        for f in (FIXTURES_DIR / "triage").glob("*.json"):
            shutil.copy(f, paths["triage"] / f.name)
        print("[4 triage] copied synthetic fixture triage outputs")
    elif args.triage == "api":
        print(f"[4 triage] api: {triage.triage_api(args.data_dir)}")
    else:
        print("[4 triage] skipped (in-session or API triage not run)")
    res = triage.validate_dir(paths["triage"], paths["triage_inputs"]) if paths["triage"].exists() else {}
    bad = {k: v for k, v in res.items() if v}
    print(f"[4 validate] {len(res) - len(bad)}/{len(res)} triage outputs valid")
    print(f"[5 route] {route.run(args.data_dir)}")
    print(f"[6 records] {records.run(args.data_dir, Path(args.records_dir) if args.records_dir else None)}")
    return 0 if m["complete"] and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
