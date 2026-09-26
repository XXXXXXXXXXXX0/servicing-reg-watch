"""Shared paths and loaders."""
from __future__ import annotations

import gzip
import json
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTER_DIR = ROOT / "register"
TAXONOMY_PATH = ROOT / "taxonomy" / "behaviors.yaml"
SCHEMA_PATH = ROOT / "pipeline" / "triage_schema.json"
PROMPT_PATH = ROOT / "pipeline" / "triage_prompt.md"
FIXTURES_DIR = ROOT / "fixtures"
RECORDS_DIR = ROOT / "records"
EVAL_LABELS_PATH = ROOT / "eval" / "labels.csv"

# Pipeline data lives under data/; override for tests or CI. Fetched source data
# (the "store") is committed as compressed files; everything derived from it is
# gitignored runtime output (see .gitignore).
DATA_DIR = Path(os.environ.get("SRW_DATA_DIR", ROOT / "data"))

# GitHub rejects files over 100 MB and warns over 50 MB; committed store files stay under this.
MAX_COMMITTED_BYTES = 50 * 1024 * 1024


def data_paths(data_dir: Path | None = None) -> dict[str, Path]:
    d = Path(data_dir) if data_dir else DATA_DIR
    return {
        "root": d,
        # committed store: fetched once, never refetched
        "fr_store": d / "raw" / "federal_register.jsonl.gz",  # FR metadata, one record per document
        "manifest": d / "raw" / "ingest_manifest.json",
        "html": d / "raw" / "govinfo",   # GovInfo responses as fetched, <doc>.htm.gz
        "ecfr": d / "raw" / "ecfr",      # eCFR point-in-time text, *.xml.gz
        "fr_search": d / "raw" / "fr_search",  # eval sample term searches, *.json.gz
        # runtime (gitignored), rebuilt from the store
        "raw": d / "raw" / "federal_register",
        "text": d / "raw" / "text",      # tag-stripped text derived from html/
        "prefilter": d / "prefilter",
        "diffs": d / "diffs",
        "triage_inputs": d / "triage_inputs",
        "triage": d / "triage",
        "queue": d / "queue",
    }


def eval_doc_ids(path: Path | None = None) -> list[str]:
    """Document numbers of the eval sample: the doc_id column of eval/labels.csv only."""
    import csv
    path = Path(path or EVAL_LABELS_PATH)
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return [r["doc_id"] for r in csv.DictReader(f) if r.get("doc_id")]


def triage_rows(data_dir: Path | None = None, include_eval: bool = False) -> list[dict]:
    """Prefilter rows of the documents that get full text, a diff and a triage
    packet: the prefilter survivors, plus, with include_eval, every eval sample
    document whatever its prefilter decision (so each one gets a prediction)."""
    paths = data_paths(data_dir)
    rows = read_jsonl(paths["prefilter"] / "kept.jsonl")
    if include_eval:
        have = {r["document_number"] for r in rows}
        want = set(eval_doc_ids()) - have
        rows += [r for r in read_jsonl(paths["prefilter"] / "dropped.jsonl") if r["document_number"] in want]
    return rows


def load_taxonomy() -> dict:
    return yaml.safe_load(TAXONOMY_PATH.read_text())


def behavior_class_ids() -> list[str]:
    return list(load_taxonomy()["behavior_classes"].keys())


def register_files() -> list[Path]:
    return [REGISTER_DIR / "federal.yaml", *sorted((REGISTER_DIR / "states").glob("*.yaml"))]


def load_register() -> list[dict]:
    rows = []
    for path in register_files():
        for row in yaml.safe_load(path.read_text()).get("rows", []):
            row = dict(row)
            row["_file"] = str(path.relative_to(ROOT))
            rows.append(row)
    return rows


def load_backlog() -> list[dict]:
    path = REGISTER_DIR / "research_backlog.yaml"
    return yaml.safe_load(path.read_text()).get("items", []) if path.exists() else []


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=False, default=str) + "\n")


def read_json(path: Path):
    return json.loads(Path(path).read_text())


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def _check_size(path: Path) -> None:
    size = Path(path).stat().st_size
    if size > MAX_COMMITTED_BYTES:
        raise RuntimeError(f"{path} is {size} bytes, over the {MAX_COMMITTED_BYTES}-byte limit for committed data; shard it")


def write_gz_text(path: Path, text: str) -> None:
    """Write a committed store file. mtime=0 keeps unchanged content byte-identical."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as f:
        f.write(text.encode("utf-8"))
    _check_size(path)


def read_gz_text(path: Path) -> str:
    with gzip.open(path, "rb") as f:
        return f.read().decode("utf-8")


def write_jsonl_gz(path: Path, rows) -> None:
    write_gz_text(path, "".join(json.dumps(r, sort_keys=True, default=str) + "\n" for r in rows))


def read_jsonl_gz(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    return [json.loads(line) for line in read_gz_text(path).splitlines() if line.strip()]
