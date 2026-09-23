import csv
import json
import re
import subprocess
import sys
import types
from pathlib import Path

import pytest

from pipeline import prefilter, route, triage
from pipeline.common import ROOT, behavior_class_ids, load_register
from pipeline.diff import xml_to_lines

FIX = ROOT / "fixtures" / "triage"


def _doc(title, abstract=None, agency="federal-communications-commission", typ="Notice", cfr=()):
    return {"document_number": "X", "title": title, "abstract": abstract, "type": typ,
            "agencies": [{"slug": agency}], "cfr_references": [{"title": t, "part": p} for t, p in cfr]}


# ---------------------------------------------------------------- prefilter
def test_prefilter_rules():
    assert prefilter.classify(_doc("Television Broadcasting Services; Anytown"))["reason"] == "noise_title"
    assert prefilter.classify(_doc("Advanced Methods To Target and Eliminate Unlawful Robocalls"))["keep"]
    assert prefilter.classify(_doc("Privacy Act of 1974; System of Records", agency="federal-trade-commission"))["keep"] is False
    # withdrawal by a finance agency is kept even without domain terms; FCC withdrawal is not
    assert prefilter.classify(_doc("Rescission of Policy", agency="comptroller-of-the-currency"))["reason"] == "withdrawal_or_rescission"
    assert prefilter.classify(_doc("Withdrawal of Proposed Rule on Tower Siting"))["keep"] is False
    # tracked CFR part beats a noise title
    assert prefilter.classify(_doc("Sunshine Act Meeting", cfr=[(12, "1006")]))["reason"] == "tracked_cfr_part"
    # case-sensitive acronym: "ai" inside words does not match
    assert prefilter.classify(_doc("Maintenance of Fair Claims"))["keep"] is False


# --------------------------------------------------------------------- diff
def test_xml_to_lines():
    xml = "<DIV8><HEAD>§ 1 Head.</HEAD><P>(a) One <I>two</I>.</P><P>(b)  Three</P></DIV8>"
    assert xml_to_lines(xml) == ["§ 1 Head.", "(a) One two.", "(b) Three"]


# ------------------------------------------------------------------- triage
def _valid():
    return json.loads((FIX / "FIXTURE-0001.json").read_text())


def test_fixture_outputs_validate():
    res = triage.validate_dir(FIX)
    assert res and all(v == [] for v in res.values()), res


@pytest.mark.parametrize("mutate,needle", [
    (lambda o: o.update(change_type="rule"), "schema"),
    (lambda o: o.update(confidence=1.2), "schema"),
    (lambda o: o.update(extra="x"), "schema"),
    (lambda o: o.pop("rationale"), "schema"),
    (lambda o: o.update(effective_date="June 1"), "schema"),
    (lambda o: o.update(behavior_classes=["CONTACT.NOPE"]), "schema"),
    (lambda o: o.update(affected_register_rows=["REGF-NOPE-999"]), "unknown register row"),
    (lambda o: o.update(behavior_classes=[]), "at least one behavior class"),
    (lambda o: o.update(doc_id="OTHER-1"), "does not match"),
])
def test_invalid_outputs_rejected(mutate, needle):
    o = _valid()
    mutate(o)
    errs = triage.validate_output(o, "FIXTURE-0001")
    assert any(needle in e for e in errs), errs


def test_validate_cli_exit_code(tmp_path):
    bad = _valid()
    bad["change_type"] = "nope"
    (tmp_path / "FIXTURE-0001.json").write_text(json.dumps(bad))
    assert triage.main(["validate", "--dir", str(tmp_path)]) == 1
    (tmp_path / "FIXTURE-0001.json").write_text(json.dumps(_valid()))
    assert triage.main(["validate", "--dir", str(tmp_path)]) == 0


def test_schema_enum_matches_taxonomy():
    schema = triage.load_schema()
    assert schema["properties"]["behavior_classes"]["items"]["enum"] == behavior_class_ids()


def test_api_schema_strips_unsupported_keywords():
    s = json.dumps(triage.api_schema())
    for k in ("pattern", "minimum", "maximum", "minLength", "uniqueItems", "$schema"):
        assert f'"{k}"' not in s
    assert triage.api_schema()["properties"]["effective_date"] == {"anyOf": [{"type": "string"}, {"type": "null"}]}


def test_system_prompt_contains_register_and_schema():
    sp = triage.system_prompt()
    assert "REGF-FREQ-001" in sp and "compliant_agent_must_now" in sp and "auto-closes" in sp


def test_api_mode_requires_key(offline_run, monkeypatch):
    pytest.importorskip("anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        triage.triage_api(offline_run["data"])


def test_api_mode_with_stubbed_client(offline_run, monkeypatch):
    """Exercise API mode end to end against a stub; no network."""
    pytest.importorskip("anthropic")
    from pipeline.common import data_paths
    p = data_paths(offline_run["data"])
    for f in p["triage"].glob("*.json"):
        f.unlink()
    calls = []

    class FakeMessages:
        def create(self, **kw):
            calls.append(kw)
            doc_id = json.loads(kw["messages"][0]["content"])["doc_id"]
            out = {**_valid(), "doc_id": doc_id}
            if doc_id == "FIXTURE-0002":
                out["affected_register_rows"] = ["MADE-UP-001"]  # must be rejected
            return types.SimpleNamespace(stop_reason="end_turn", usage=None,
                                         content=[types.SimpleNamespace(type="text", text=json.dumps(out))])

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", lambda: types.SimpleNamespace(messages=FakeMessages()))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-key")
    monkeypatch.delenv("MODEL", raising=False)
    stats = triage.triage_api(offline_run["data"], limit=3)
    assert stats == {"ok": 2, "invalid": 1, "errors": 0, "skipped_full_text_unavailable": 6}
    assert calls[0]["model"] == "claude-sonnet-5"
    assert calls[0]["output_config"]["format"]["type"] == "json_schema"
    assert calls[0]["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert (p["triage"] / "_rejected" / "FIXTURE-0002.json").exists()
    assert not (p["triage"] / "FIXTURE-0002.json").exists()


# -------------------------------------------------------------------- route
@pytest.mark.parametrize("triage_out,errors,expected", [
    ({"relevant": False, "confidence": 0.85}, [], ("auto_closed", "not_relevant_high_confidence")),
    ({"relevant": False, "confidence": 0.8499}, [], ("review", "not_relevant_low_confidence")),
    ({"relevant": True, "confidence": 0.99}, [], ("review", "relevant")),
    ({"relevant": False, "confidence": 0.99}, ["bad"], ("review", "invalid_triage_output")),
    (None, None, ("review", "untriaged")),
])
def test_route_rule(triage_out, errors, expected):
    assert route.decide(triage_out, errors) == expected


def test_route_full_text_unavailable_overrides_triage():
    out = {"relevant": False, "confidence": 0.99}
    assert route.decide(out, [], has_full_text=False) == ("review", "full_text_unavailable")
    assert route.decide(None, None, has_full_text=False) == ("review", "full_text_unavailable")


# ----------------------------------------------------------------- register
def test_register_rows_complete_and_valid():
    from pipeline.inventory import validate_rows
    rows = load_register()
    assert validate_rows(rows) == []
    for r in rows:
        assert r["provenance"] and r["status"]
        if r["status"] == "unresearched":
            assert r["citation"] is None and r["source_url"] is None
            continue
        assert r["citation"] and r["source_url"].startswith("http")
        if r["jurisdiction"] != "federal" and not r.get("last_checked"):
            assert r["status"] == "verify"


def test_unresearched_rows_cannot_carry_citations():
    from pipeline.inventory import validate_rows
    row = next(r for r in load_register() if r["status"] == "unresearched")
    assert validate_rows([{**row, "citation": "made up"}]) != []
    assert validate_rows([{**row, "status": "verify"}]) != []


def test_inventory_regenerates_from_yaml():
    from pipeline import inventory
    assert inventory.main(["--check"]) == 0


# --------------------------------------------------------------------- eval
def test_eval_scores_fixture_labels(offline_run, tmp_path):
    import run_eval
    labels = tmp_path / "labels.csv"
    rows = [
        ("FIXTURE-0001", "Y", "CONTACT.FREQUENCY;CONTACT.AI_DISCLOSURE", "1"),  # TP, exact classes
        ("FIXTURE-0002", "Y", "PAYMENT.FEES;NEGOTIATION.TREATMENT", "1"),        # TP, partial
        ("FIXTURE-0006", "N", "", ""),                                           # TN (triage)
        ("FIXTURE-0005", "N", "", ""),                                           # TN (prefilter drop)
        ("FIXTURE-0012", "Y", "CONTACT.CONSENT", "1"),                           # FN
        ("FIXTURE-0011", "Y", "DATA.PRIVACY_SECURITY", "2"),                     # untriaged -> missing
        ("FIXTURE-0015", "", "", ""),                                            # unlabeled
    ]
    with open(labels, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["doc_id", "title", "html_url", "label_relevant", "label_behavior_classes", "label_tier",
                    "labeled_by", "labeled_on", "notes"])
        for d, rel, cls, tier in rows:
            w.writerow([d, "", "", rel, cls, tier, "test", "", ""])
    out = tmp_path / "results.md"
    assert run_eval.main(["--labels", str(labels), "--data-dir", str(offline_run["data"]), "--out", str(out)]) == 0
    text = out.read_text()
    assert "TP 2" in text and "FP 0" in text and "FN 1" in text and "TN 2" in text
    assert "Exact set match: 1/2" in text
    assert "FIXTURE-0011" in text  # reported as missing
    assert "Sample-size caveat" in text


def test_eval_without_labels_writes_status(tmp_path):
    import run_eval
    out = tmp_path / "results.md"
    assert run_eval.main(["--labels", str(ROOT / "eval" / "labels.csv"), "--data-dir", str(tmp_path), "--out", str(out)]) == 0
    assert "No results yet" in out.read_text()


def test_clopper_pearson_known_values():
    import run_eval
    lo, hi = run_eval.clopper_pearson(15, 15)
    assert abs(lo - 0.025 ** (1 / 15)) < 1e-9 and hi == 1.0
    lo, hi = run_eval.clopper_pearson(7, 10)
    assert abs(lo - 0.3475) < 1e-3 and abs(hi - 0.9333) < 1e-3


def test_sample_selection(offline_run, tmp_path):
    import select_sample
    rc = select_sample.main(["--data-dir", str(offline_run["data"]), "--out-dir", str(tmp_path)])
    assert rc == 0
    with open(tmp_path / "labels.csv") as f:
        rows = list(csv.DictReader(f))
    assert rows and all(r["label_relevant"] == "" for r in rows)
    assert select_sample.main(["--data-dir", str(offline_run["data"]), "--out-dir", str(tmp_path)]) == 1  # no overwrite


# ------------------------------------------------------------------ secrets
SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"ANTHROPIC_API_KEY\s*[=:]\s*['\"]?[A-Za-z0-9_-]{20,}"),
]


def test_no_secrets_in_tracked_files():
    files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                           cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    hits = []
    for rel in files:
        path = ROOT / rel
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        text = path.read_text(errors="ignore")
        hits += [f"{rel}: {p.pattern}" for p in SECRET_PATTERNS if p.search(text)]
    assert hits == []
