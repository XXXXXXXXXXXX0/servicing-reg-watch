"""Shared paths and loaders."""
from __future__ import annotations

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

# Runtime data lives outside git by default; override for tests or CI.
DATA_DIR = Path(os.environ.get("SRW_DATA_DIR", ROOT / "data"))


def data_paths(data_dir: Path | None = None) -> dict[str, Path]:
    d = Path(data_dir) if data_dir else DATA_DIR
    return {
        "root": d,
        "raw": d / "raw" / "federal_register",
        "manifest": d / "raw" / "ingest_manifest.json",
        "text": d / "raw" / "text",
        "prefilter": d / "prefilter",
        "diffs": d / "diffs",
        "triage_inputs": d / "triage_inputs",
        "triage": d / "triage",
        "queue": d / "queue",
    }


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
