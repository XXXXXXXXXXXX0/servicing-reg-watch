"""Step 4 - Triage.

Triage instructions live in pipeline/triage_prompt.md. Output for each document
is one JSON file, data/triage/<doc_id>.json, that validates against
pipeline/triage_schema.json. Two ways to produce it:

  in-session : an operator reads the prompt, register and packets and writes
               the JSON files by hand, then runs `validate`.
  api        : optional; calls the Anthropic API (MODEL env, default
               claude-sonnet-5; key from ANTHROPIC_API_KEY).

    python -m pipeline.triage inputs   [--data-dir DIR] [--include-eval]  # build packets
    python -m pipeline.triage prompt   [--data-dir DIR]  # write assembled system prompt
    python -m pipeline.triage status   [--data-dir DIR]  # packets lacking output
    python -m pipeline.triage validate [--data-dir DIR | --dir DIR]
    python -m pipeline.triage api      [--data-dir DIR] [--limit N] [--force]
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import sys
from pathlib import Path

import jsonschema

from .common import (PROMPT_PATH, SCHEMA_PATH, behavior_class_ids, data_paths, load_register,
                     load_taxonomy, read_json, triage_rows, write_json)

DEFAULT_MODEL = "claude-sonnet-5"
TEXT_EXCERPT_CHARS = 20000
DIFF_EXCERPT_CHARS = 12000


# ----------------------------------------------------------------- packets
def build_packet(doc: dict, prefilter_row: dict, diff: dict | None, text: str | None,
                 text_missing_reason: str | None = None) -> dict:
    packet = {
        "doc_id": doc["document_number"],
        "metadata": {k: doc.get(k) for k in (
            "document_number", "title", "type", "subtype", "action", "publication_date",
            "effective_on", "dates", "cfr_references", "citation", "docket_ids",
            "regulation_id_numbers", "html_url")},
        "agencies": [a.get("name") or a.get("raw_name") for a in doc.get("agencies", [])],
        "abstract": doc.get("abstract"),
        "prefilter": {k: prefilter_row.get(k) for k in ("reason", "exclude", "cfr_hits", "cfpb_type", "keyword_hits")},
        "full_text_available": bool(text),
        "full_text_missing_reason": None if text else (text_missing_reason or "not fetched"),
        "full_text_excerpt": None,
        "full_text_truncated": False,
        "ecfr_diff": None,
    }
    if text:
        packet["full_text_excerpt"] = text[:TEXT_EXCERPT_CHARS]
        packet["full_text_truncated"] = len(text) > TEXT_EXCERPT_CHARS
    if diff:
        d = copy.deepcopy(diff)
        budget = DIFF_EXCERPT_CHARS
        for s in d.get("sections", []):
            u = s.get("unified_diff", "")
            s["unified_diff"] = u[:max(budget, 0)]
            s["diff_truncated"] = len(u) > max(budget, 0)
            budget -= len(u)
        packet["ecfr_diff"] = d
    return packet


def build_inputs(data_dir=None, include_eval: bool = False) -> int:
    paths = data_paths(data_dir)
    n = 0
    missing_path = paths["text"] / "_missing.json"
    missing = read_json(missing_path) if missing_path.exists() else {}
    for row in triage_rows(data_dir, include_eval):
        num = row["document_number"]
        doc = read_json(paths["raw"] / f"{num}.json")["document"]
        diff_path = paths["diffs"] / f"{num}.json"
        text_path = paths["text"] / f"{num}.txt"
        packet = build_packet(
            doc, row,
            read_json(diff_path) if diff_path.exists() else None,
            text_path.read_text() if text_path.exists() else None,
            missing.get(num),
        )
        write_json(paths["triage_inputs"] / f"{num}.json", packet)
        n += 1
    return n


# ------------------------------------------------------------------ prompt
def register_context() -> list[dict]:
    keep = ("id", "law", "citation", "jurisdiction", "applies_to", "tier", "behavior_classes", "constraint", "status")
    return [{k: r.get(k) for k in keep} for r in load_register()]


def system_prompt() -> str:
    tax = {k: v["description"] for k, v in load_taxonomy()["behavior_classes"].items()}
    return "\n\n".join([
        PROMPT_PATH.read_text().strip(),
        "## Behavior taxonomy\n\n```json\n" + json.dumps(tax, indent=1) + "\n```",
        "## Register rows\n\n```json\n" + json.dumps(register_context(), indent=1, default=str) + "\n```",
        "## Output JSON schema\n\n```json\n" + SCHEMA_PATH.read_text().strip() + "\n```",
    ])


# -------------------------------------------------------------- validation
def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def class_tags(obj: dict) -> tuple[list[str], list[str]]:
    """(primary, secondary) behavior classes. A v1 output has one undivided
    `behavior_classes` list; it is returned as primary, since v1 made no split."""
    if "behavior_classes_primary" in obj or "behavior_classes_secondary" in obj:
        return list(obj.get("behavior_classes_primary", [])), list(obj.get("behavior_classes_secondary", []))
    return list(obj.get("behavior_classes", [])), []


def validate_output(obj, expected_doc_id: str | None = None, register_ids: set | None = None) -> list[str]:
    """Schema validation plus semantic checks. Returns a list of error strings."""
    errors = [f"schema: {e.message} at /{'/'.join(map(str, e.path))}"
              for e in jsonschema.Draft202012Validator(load_schema()).iter_errors(obj)]
    if errors or not isinstance(obj, dict):
        return errors
    if expected_doc_id is not None and obj["doc_id"] != expected_doc_id:
        errors.append(f"doc_id {obj['doc_id']!r} does not match file/packet {expected_doc_id!r}")
    ids = register_ids if register_ids is not None else {r["id"] for r in load_register()}
    unknown = [r for r in obj["affected_register_rows"] if r not in ids]
    if unknown:
        errors.append(f"unknown register row ids: {unknown}")
    primary, secondary = class_tags(obj)
    if "behavior_classes" in obj and ("behavior_classes_primary" in obj or "behavior_classes_secondary" in obj):
        errors.append("use either v1 behavior_classes or v1.1 behavior_classes_primary/secondary, not both")
    if set(primary) & set(secondary):
        errors.append(f"classes in both primary and secondary: {sorted(set(primary) & set(secondary))}")
    if obj["relevant"]:
        if not primary:
            errors.append("relevant=true requires at least one behavior class (primary, in v1.1 output)")
        for field in ("what_changed", "compliant_agent_must_now"):
            if not obj[field].strip():
                errors.append(f"relevant=true requires non-empty {field}")
    return errors


def validate_dir(triage_dir: Path, inputs_dir: Path | None = None) -> dict[str, list[str]]:
    register_ids = {r["id"] for r in load_register()}
    results = {}
    for f in sorted(Path(triage_dir).glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            obj = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            results[f.name] = [f"invalid JSON: {e}"]
            continue
        errs = validate_output(obj, f.stem, register_ids)
        if inputs_dir is not None and not (Path(inputs_dir) / f.name).exists():
            errs.append("no matching triage input packet")
        results[f.name] = errs
    return results


def full_text_available(packet: dict) -> bool:
    """Packets built before this flag existed are treated as having full text."""
    return packet.get("full_text_available", True)


def pending(data_dir=None) -> list[str]:
    """Packets awaiting triage. Packets without full text are not triaged; route.py
    sends them to human review (reason full_text_unavailable)."""
    paths = data_paths(data_dir)
    done = {p.stem for p in paths["triage"].glob("*.json")}
    return sorted(p.stem for p in paths["triage_inputs"].glob("*.json")
                  if not p.name.startswith("_") and p.stem not in done
                  and full_text_available(read_json(p)))


def log_run(data_dir, doc_id: str, mode: str, **extra) -> None:
    paths = data_paths(data_dir)
    paths["triage"].mkdir(parents=True, exist_ok=True)
    with open(paths["triage"] / "_runlog.jsonl", "a") as f:
        f.write(json.dumps({"doc_id": doc_id, "mode": mode,
                            "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **extra}) + "\n")


# ---------------------------------------------------------------- API mode
_UNSUPPORTED_KEYS = {"$schema", "$id", "title", "minimum", "maximum", "minLength", "pattern", "uniqueItems"}


def api_schema(schema: dict | None = None):
    """Structured-output version of the schema: keywords the API may reject are
    stripped. Full validation still runs locally on every response."""
    def strip(node):
        if isinstance(node, dict):
            out = {k: strip(v) for k, v in node.items() if k not in _UNSUPPORTED_KEYS}
            if isinstance(out.get("type"), list):  # ["string","null"] -> anyOf
                types = out.pop("type")
                out = {"anyOf": [{**out, "type": t} if t != "null" else {"type": "null"} for t in types]}
            return out
        if isinstance(node, list):
            return [strip(v) for v in node]
        return node
    schema = copy.deepcopy(schema or load_schema())
    # The API gets the v1.1 shape only: primary/secondary lists, no v1 behavior_classes.
    if schema.pop("anyOf", None) is not None:
        schema["properties"].pop("behavior_classes", None)
        schema["required"] = schema["required"] + ["behavior_classes_primary", "behavior_classes_secondary"]
    return strip(schema)


def triage_api(data_dir=None, limit: int | None = None, force: bool = False) -> dict:
    import anthropic  # optional dependency; only API mode needs it

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set; API mode unavailable. Use in-session mode instead.")
    model = os.environ.get("MODEL", DEFAULT_MODEL)
    client = anthropic.Anthropic()
    paths = data_paths(data_dir)
    system = [{"type": "text", "text": system_prompt(), "cache_control": {"type": "ephemeral"}}]
    fmt = {"format": {"type": "json_schema", "schema": api_schema()}}
    register_ids = {r["id"] for r in load_register()}
    todo = sorted(p.stem for p in paths["triage_inputs"].glob("*.json") if not p.name.startswith("_"))
    if not force:
        todo = [d for d in todo if not (paths["triage"] / f"{d}.json").exists()]
    # Do not triage from partial information; route.py sends these to human review.
    no_text = [d for d in todo if not full_text_available(read_json(paths["triage_inputs"] / f"{d}.json"))]
    todo = [d for d in todo if d not in no_text]
    todo = todo[:limit] if limit else todo
    stats = {"ok": 0, "invalid": 0, "errors": 0}
    if no_text:
        stats["skipped_full_text_unavailable"] = len(no_text)
    for doc_id in todo:
        packet = read_json(paths["triage_inputs"] / f"{doc_id}.json")
        try:
            resp = client.messages.create(
                model=model, max_tokens=16000, system=system, output_config=fmt,
                messages=[{"role": "user", "content": json.dumps(packet)}],
            )
        except anthropic.RateLimitError as e:
            log_run(data_dir, doc_id, "api", model=model, error=f"rate_limited: {e}")
            stats["errors"] += 1
            continue
        except anthropic.APIStatusError as e:
            log_run(data_dir, doc_id, "api", model=model, error=f"http_{e.status_code}: {e.message}")
            stats["errors"] += 1
            continue
        except anthropic.APIConnectionError as e:
            log_run(data_dir, doc_id, "api", model=model, error=f"connection: {e}")
            stats["errors"] += 1
            continue
        if resp.stop_reason in ("refusal", "max_tokens"):
            log_run(data_dir, doc_id, "api", model=model, error=f"stop_reason={resp.stop_reason}")
            stats["errors"] += 1
            continue
        text = next((b.text for b in resp.content if b.type == "text"), "")
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            log_run(data_dir, doc_id, "api", model=model, error=f"invalid JSON: {e}")
            stats["invalid"] += 1
            continue
        errs = validate_output(obj, doc_id, register_ids)
        if errs:
            write_json(paths["triage"] / "_rejected" / f"{doc_id}.json", {"output": obj, "errors": errs})
            log_run(data_dir, doc_id, "api", model=model, error="validation", details=errs)
            stats["invalid"] += 1
            continue
        write_json(paths["triage"] / f"{doc_id}.json", obj)
        log_run(data_dir, doc_id, "api", model=model, usage=resp.usage.model_dump() if resp.usage else None)
        stats["ok"] += 1
    return stats


# --------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["inputs", "prompt", "status", "validate", "api"])
    ap.add_argument("--data-dir")
    ap.add_argument("--dir", help="validate: directory of triage JSON (default data/triage)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--include-eval", action="store_true", help="inputs: also the eval sample (eval/labels.csv)")
    args = ap.parse_args(argv)
    paths = data_paths(args.data_dir)
    if args.command == "inputs":
        print(f"triage inputs: {build_inputs(args.data_dir, args.include_eval)} packets -> {paths['triage_inputs']}")
    elif args.command == "prompt":
        out = paths["triage_inputs"] / "_system_prompt.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(system_prompt() + "\n")
        print(f"wrote {out}")
    elif args.command == "status":
        todo = pending(args.data_dir)
        print(f"{len(todo)} packets without triage output")
        for d in todo:
            print(f"  {d}")
    elif args.command == "validate":
        tdir = Path(args.dir) if args.dir else paths["triage"]
        res = validate_dir(tdir, None if args.dir else paths["triage_inputs"])
        bad = {k: v for k, v in res.items() if v}
        print(f"validate: {len(res) - len(bad)}/{len(res)} valid in {tdir}")
        for k, v in bad.items():
            for e in v:
                print(f"  {k}: {e}")
        return 1 if bad else 0
    elif args.command == "api":
        print(f"triage api: {triage_api(args.data_dir, args.limit, args.force)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
