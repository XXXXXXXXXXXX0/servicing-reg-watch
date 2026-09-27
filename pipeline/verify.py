"""Register pre-check: fetch the primary text behind register rows, and render
register/VERIFICATION_REPORT.md from the rows' machine_check and preemption fields.

    python -m pipeline.verify fetch    # fetch sources in register/primary_sources.yaml not yet in the store
    python -m pipeline.verify report   # write register/VERIFICATION_REPORT.md from the register YAML
    python -m pipeline.verify report --check   # fail if the report is stale

Every response is saved to the committed store before use and never refetched:
eCFR text in data/raw/ecfr/ (same keys as the diff step), Federal Register text
in data/raw/govinfo/, U.S. Code and state pages in data/raw/primary/.
Tag-stripped copies go to data/verify/<source>.txt (runtime) for review.

The comparison itself (match / mismatch / not_checkable) is a reviewed judgment
recorded in each row's machine_check field; nothing here changes a row's status.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

from . import config
from .common import REGISTER_DIR, data_paths, load_register, read_gz_text, write_gz_text
from .sources import Blocked, EcfrTextCache, NotFound, TextUnavailable, html_to_text

SOURCES_PATH = REGISTER_DIR / "primary_sources.yaml"
REPORT_PATH = REGISTER_DIR / "VERIFICATION_REPORT.md"
USCODE_URL = "https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title{title}-section{section}&num=0&edition=prelim"

MACHINE_CHECK_RESULTS = {"match", "mismatch", "not_checkable"}
PREEMPTION_TYPES = {"floor", "express_preemption", "mixed", "none_stated", "not_applicable"}
STRICTER = {"stricter", "not_stricter", "different_scope", "unclear"}


def load_sources(path: Path = SOURCES_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text())


def primary_path(name: str, data_dir=None) -> Path:
    return data_paths(data_dir)["root"] / "raw" / "primary" / f"{name}.htm.gz"


def fetch_source(client, key: str, spec: dict, ecfr_date: str, data_dir=None) -> tuple[str, str]:
    """(raw text, store path) for one source, from the store when present."""
    paths = data_paths(data_dir)
    kind = spec["kind"]
    if kind == "blocked":
        raise TextUnavailable(spec["reason"])
    if kind == "ecfr":
        params = {"part": spec["part"]}
        for k in ("section", "appendix", "subpart"):
            if k in spec:
                params[k] = spec[k]
        url = f"{config.ECFR_API}/full/{ecfr_date}/title-{spec['title']}.xml"
        cache = EcfrTextCache(client, paths["ecfr"])
        key_name = url[len(f"{config.ECFR_API}/full/"):] + "".join(f"_{k}-{v}" for k, v in sorted(params.items()))
        store = paths["ecfr"] / (re.sub(r"[^A-Za-z0-9.-]+", "_", key_name) + ".gz")
        return cache.get_text(url, params), str(store)
    if kind == "govinfo":
        store = paths["html"] / f"{spec['document_number']}.htm.gz"
        if not store.exists():
            markup, _route = client.get_document_html(spec)
            write_gz_text(store, markup)
        return read_gz_text(store), str(store)
    if kind in ("uscode", "url"):
        url = USCODE_URL.format(**spec) if kind == "uscode" else spec["url"]
        name = f"uscode/title{spec['title']}-section{spec['section']}" if kind == "uscode" else spec["name"]
        store = primary_path(name, data_dir)
        if not store.exists():
            write_gz_text(store, client.get_text(url))
        return read_gz_text(store), str(store)
    raise ValueError(f"{key}: unknown kind {kind}")


def _fix_mojibake(text: str) -> str:
    """Undo UTF-8 read as Latin-1 (responses without a charset, e.g. eCFR XML) in the review copy only."""
    if "\u00c2" in text or "\u00e2\u0080" in text:
        try:
            return text.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text
    return text


def fetch_all(client, data_dir=None, only: set | None = None) -> dict:
    spec = load_sources()
    out_dir = data_paths(data_dir)["root"] / "verify"
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = [], {}
    for key, s in spec["sources"].items():
        if only and key not in only:
            continue
        try:
            raw, _store = fetch_source(client, key, s, str(spec["ecfr_date"]), data_dir)
        except (NotFound, Blocked, TextUnavailable) as e:
            failed[key] = f"{type(e).__name__}: {e}"
            continue
        except Exception as e:  # network errors: record and carry on with the rest
            failed[key] = f"{type(e).__name__}"
            continue
        text = _fix_mojibake(html_to_text(raw))
        (out_dir / f"{key}.txt").write_text(re.sub(r"\n\s*\n+", "\n", text))
        ok.append(key)
    return {"fetched_or_cached": len(ok), "failed": failed}


# ----------------------------------------------------------------- report
def _q(s) -> str:
    return str(s or "").replace("|", "\\|").replace("\n", " ").strip()


CORE_ROWS = [
    ("Regulation F call frequency", ["REGF-FREQ-001"]),
    ("Regulation F time and place of contact", ["REGF-TIME-001", "REGF-TIME-002"]),
    ("TCPA consent", ["TCPA-CONSENT-001"]),
    ("FCC ruling on AI-generated voices", ["TCPA-AIVOICE-001"]),
    ("Regulation E preauthorized transfers", ["REGE-PREAUTH-001", "REGE-PREAUTH-002"]),
    ("Bankruptcy automatic stay", ["BK-STAY-001"]),
    ("Massachusetts call limit", ["MA-940CMR-001"]),
    ("California Rosenthal Act incorporation of the FDCPA", ["CA-ROSENTHAL-001"]),
]


def _row_block(r: dict) -> list[str]:
    mc = r.get("machine_check") or {}
    lines = [f"#### {r['id']} ({r['law']})", "",
             f"- Citation (row): {r.get('citation')}",
             f"- Constraint (row): {r.get('constraint')}",
             f"- machine_check: **{mc.get('result', 'missing')}** ({mc.get('date', '')})"]
    for s in mc.get("sources") or []:
        lines.append(f"  - source: `{s}`")
    if mc.get("note"):
        lines.append(f"- Note: {mc['note']}")
    for m in mc.get("mismatches") or []:
        lines.append(f"- Mismatch: row says \"{m['row_says']}\"; {m['source_cite']} says \"{m['source_says']}\"")
    p = r.get("preemption")
    if p:
        lines.append(f"- Preemption: **{p['type']}**" + (f" ({p['citation']}): \"{p['quote']}\"" if p.get("quote") else "")
                     + (f" {p['note']}" if p.get("note") else ""))
    for i in r.get("federal_interaction") or []:
        lines.append(f"- Interacts with {i['row']}: {i['stricter']}. {i.get('note', '')}".rstrip())
    return lines + [""]


def render_report(rows: list[dict]) -> str:
    checked = [r for r in rows if r.get("status") == "verify"]
    by = {k: [r for r in checked if (r.get("machine_check") or {}).get("result") == k] for k in sorted(MACHINE_CHECK_RESULTS)}
    missing = [r for r in checked if not r.get("machine_check")]
    ids = {r["id"]: r for r in rows}
    check_date = sorted({str((r.get("machine_check") or {}).get("date")) for r in checked if r.get("machine_check")})
    out = ["# Register verification report", "",
           "Generated by `python -m pipeline.verify report` from the register YAML. "
           "A machine check compares a row's citation and constraint summary with the fetched primary text. "
           "It does not verify a row: no row's status is changed, and `verified` needs human sign-off. Not legal advice.", "",
           "Criteria. **match**: every statement in the row is supported by the cited text; omissions that make the row "
           "stricter than the law are noted, not counted. **mismatch**: the text contradicts the row (a number, period, "
           "trigger, party or finding type differs), the cited paragraph does not hold the rule attributed to it, or the "
           "row drops a condition so that following it could break the law. **not_checkable**: the primary text could not "
           "be fetched or is proprietary.", "",
           "## Summary", "",
           f"- Rows with `status: verify`: {len(checked)} (check date: {', '.join(check_date) or 'none'})",
           *[f"- {k}: {len(v)}" for k, v in by.items()],
           f"- no machine_check yet: {len(missing)}",
           f"- Rows by status: " + ", ".join(f"{s}: {sum(r['status'] == s for r in rows)}" for s in ("verify", "verified", "unresearched")),
           ""]
    nc = {}
    for r in by["not_checkable"]:
        reason = (r["machine_check"].get("reason") or "other")
        nc.setdefault(reason, []).append(r["id"])
    if nc:
        out += ["Not checkable, by reason:", ""] + [f"- {k}: {', '.join(v)}" for k, v in sorted(nc.items())] + [""]
    out += ["## Core rows", ""]
    for label, rids in CORE_ROWS:
        out += [f"### {label}", ""]
        for rid in rids:
            if rid in ids:
                out += _row_block(ids[rid])
    core = {rid for _, rids in CORE_ROWS for rid in rids}
    out += ["## Mismatches", ""]
    mm = [r for r in by["mismatch"]]
    if not mm:
        out += ["None.", ""]
    for r in mm:
        out += [f"### {r['id']}" + (" (core row, above)" if r["id"] in core else ""), ""]
        for m in r["machine_check"].get("mismatches") or []:
            out += [f"- Row wording: \"{m['row_says']}\"",
                    f"- Primary text ({m['source_cite']}): \"{m['source_says']}\"", ""]
        if r["machine_check"].get("note"):
            out += [f"- Note: {r['machine_check']['note']}", ""]
    out += ["## Preemption (federal rows)", "",
            "Types: floor (stricter state law allowed), express_preemption, mixed (floor with express exceptions). "
            "none_stated: the cited law has no provision on its relation to state law. "
            "not_applicable: private rules or supervisory guidance. No automatic conflict resolution is built.", "",
            "| Row | Type | Governing provision | Governing sentence |", "|---|---|---|---|"]
    for r in rows:
        if r.get("jurisdiction") == "federal" and r.get("preemption"):
            p = r["preemption"]
            out.append(f"| {r['id']} | {p['type']} | {_q(p.get('citation'))} | {_q(p.get('quote') or p.get('note'))} |")
    out += ["", "## State rows: federal interaction", "",
            "| State row | Federal row | Stricter? | Note |", "|---|---|---|---|"]
    for r in rows:
        for i in r.get("federal_interaction") or []:
            out.append(f"| {r['id']} | {i['row']} | {i['stricter']} | {_q(i.get('note'))} |")
    blocked = [(k, v) for k, v in load_sources()["sources"].items() if v["kind"] == "blocked"]
    if blocked:
        out += ["", "## Sources not fetched", "", "| Source | URL | Reason |", "|---|---|---|"]
        out += [f"| {k} | {_q(v['url'])} | {_q(v['reason'])} |" for k, v in blocked]
    out += ["", "## All other rows", ""]
    for r in checked:
        if r["id"] not in core:
            mc = r.get("machine_check") or {}
            out.append(f"- {r['id']}: {mc.get('result', 'missing')}" + (f" ({mc['reason']})" if mc.get("reason") else "")
                       + (f". {mc['note']}" if mc.get("note") else ""))
    return "\n".join(out) + "\n"


def validate(rows: list[dict]) -> list[str]:
    errors = []
    for r in rows:
        mc = r.get("machine_check")
        if mc is not None:
            if mc.get("result") not in MACHINE_CHECK_RESULTS:
                errors.append(f"{r['id']}: machine_check.result must be one of {sorted(MACHINE_CHECK_RESULTS)}")
            if not mc.get("date"):
                errors.append(f"{r['id']}: machine_check.date is required")
            if mc.get("result") == "mismatch" and not mc.get("mismatches"):
                errors.append(f"{r['id']}: a mismatch must quote the row wording and the conflicting sentence")
        p = r.get("preemption")
        if p is not None:
            if p.get("type") not in PREEMPTION_TYPES:
                errors.append(f"{r['id']}: preemption.type must be one of {sorted(PREEMPTION_TYPES)}")
            if p.get("type") in ("floor", "express_preemption", "mixed") and not (p.get("quote") and p.get("citation")):
                errors.append(f"{r['id']}: preemption {p.get('type')} must quote the governing sentence with its citation")
        for i in r.get("federal_interaction") or []:
            if i.get("stricter") not in STRICTER:
                errors.append(f"{r['id']}: federal_interaction.stricter must be one of {sorted(STRICTER)}")
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--only", nargs="*", help="source keys to fetch")
    r = sub.add_parser("report")
    r.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "fetch":
        from .sources import LiveClient
        res = fetch_all(LiveClient(), only=set(args.only) if args.only else None)
        print(f"fetched or cached: {res['fetched_or_cached']}; failed: {len(res['failed'])}")
        for k, v in res["failed"].items():
            print(f"  {k}: {v}")
        return 0
    rows = load_register()
    errs = validate(rows)
    if errs:
        print("\n".join(errs), file=sys.stderr)
        return 1
    text = render_report(rows)
    if args.check:
        if not REPORT_PATH.exists() or REPORT_PATH.read_text() != text:
            print(f"{REPORT_PATH} is stale; run python -m pipeline.verify report", file=sys.stderr)
            return 1
        return 0
    REPORT_PATH.write_text(text)
    print(f"wrote {REPORT_PATH.relative_to(REGISTER_DIR.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
