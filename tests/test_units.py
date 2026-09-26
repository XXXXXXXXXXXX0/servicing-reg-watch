import csv
import json
import re
import subprocess
import sys
import types
from pathlib import Path

import pytest

from pipeline import prefilter, route, triage
from pipeline.common import FIXTURES_DIR as FIXTURES, ROOT, behavior_class_ids, load_register
from pipeline.diff import xml_to_lines

FIX = ROOT / "fixtures" / "triage"


def _doc(title, abstract=None, agency="federal-communications-commission", typ="Notice", cfr=()):
    return {"document_number": "X", "title": title, "abstract": abstract, "type": typ,
            "agencies": [{"slug": agency}], "cfr_references": [{"title": t, "part": p} for t, p in cfr]}


# ---------------------------------------------------------------- prefilter
def test_prefilter_rules():
    cfpb = "consumer-financial-protection-bureau"
    c = prefilter.classify
    # EXCLUDE runs first, even over a CFR match
    assert c(_doc("Sunshine Act Meeting", cfr=[(12, "1006")]))["reason"] == "excluded_sunshine_act_meeting"
    assert c(_doc("Agency Information Collection Activities: Reg F", agency=cfpb))["reason"] == "excluded_pra_information_collection"
    assert c(_doc("Privacy Act of 1974; System of Records", agency="federal-trade-commission"))["reason"] == "excluded_privacy_act_sorn"
    assert c(_doc("Delegation of Authority", agency=cfpb))["reason"] == "excluded_agency_organization"
    assert c(_doc("Television Broadcasting Services; Anytown"))["reason"] == "excluded_fcc_spectrum_broadcast_licensing"
    assert c(_doc("Wireless Telecommunications Bureau Seeks Comment on Robocall Mitigation"))["reason"] == "C_keyword"
    # A: CFR parts, exact list
    assert c(_doc("Anything", cfr=[(12, "748")]))["reason"] == "A_cfr_part"
    assert c(_doc("Anything", cfr=[(12, "1090")]))["reason"] == "A_cfr_part"
    assert c(_doc("Anything", cfr=[(12, "1024")]))["reason"] == "no_match"
    # B: CFPB types
    assert c(_doc("Rules of Practice", agency=cfpb, typ="Rule"))["cfpb_type"] == "final_rule"
    assert c(_doc("Supervisory Highlights, Issue 35", agency=cfpb))["cfpb_type"] == "supervisory highlights"
    assert c(_doc("Withdrawal of Guidance Documents", agency=cfpb))["cfpb_type"] == "guidance_withdrawal_or_rescission"
    assert c(_doc("Consumer Credit Card Market Report", agency=cfpb))["reason"] == "no_match"
    assert c(_doc("Rescission of Policy", agency="comptroller-of-the-currency"))["reason"] == "no_match"
    # C: whole words, optional plural, stems, case-sensitive acronyms
    assert c(_doc("Advanced Methods To Target and Eliminate Unlawful Robocalls"))["keyword_hits"] == ["robocall"]
    assert c(_doc("Loan Delinquency Reporting", agency=cfpb))["keyword_hits"] == ["delinquen*"]
    assert c(_doc("GAP Waivers", agency=cfpb))["keyword_hits"] == ["GAP waiver"]
    assert c(_doc("Gap waiver", agency=cfpb))["keep"] is False
    assert c(_doc("Achieving ach Goals", agency=cfpb))["keep"] is False
    assert c(_doc("Robot Rules", agency=cfpb))["keep"] is False
    assert c(_doc("Title", abstract="Third party relationships", agency=cfpb))["keyword_hits"] == ["third-party relationship"]


def test_prefilter_coverage_reaches_every_row_and_class():
    cov = prefilter.coverage()
    assert cov["unreached_rows"] == [] and cov["unreached_classes"] == []


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


def _v11(o, primary, secondary):
    o.pop("behavior_classes")
    o.update(behavior_classes_primary=primary, behavior_classes_secondary=secondary)
    return o


def test_v1_1_primary_secondary_tags():
    o = _v11(_valid(), ["CONTACT.FREQUENCY"], ["CONTACT.AI_DISCLOSURE"])
    assert triage.validate_output(o, "FIXTURE-0001") == []
    assert triage.class_tags(o) == (["CONTACT.FREQUENCY"], ["CONTACT.AI_DISCLOSURE"])
    assert triage.class_tags(_valid()) == (_valid()["behavior_classes"], [])  # v1: undivided list reads as primary
    o["change_type"] = "interpretation"
    assert triage.validate_output(o, "FIXTURE-0001") == []
    both = _v11(_valid(), ["CONTACT.FREQUENCY"], ["CONTACT.FREQUENCY"])
    assert any("both primary and secondary" in e for e in triage.validate_output(both, "FIXTURE-0001"))
    no_primary = _v11(_valid(), [], ["CONTACT.FREQUENCY"])
    assert any("at least one behavior class" in e for e in triage.validate_output(no_primary, "FIXTURE-0001"))
    mixed = _valid()
    mixed.update(behavior_classes_primary=["CONTACT.FREQUENCY"], behavior_classes_secondary=[])
    assert any("not both" in e for e in triage.validate_output(mixed, "FIXTURE-0001"))
    neither = _valid()
    neither.pop("behavior_classes")
    assert any(e.startswith("schema") for e in triage.validate_output(neither, "FIXTURE-0001"))


def test_validate_cli_exit_code(tmp_path):
    bad = _valid()
    bad["change_type"] = "nope"
    (tmp_path / "FIXTURE-0001.json").write_text(json.dumps(bad))
    assert triage.main(["validate", "--dir", str(tmp_path)]) == 1
    (tmp_path / "FIXTURE-0001.json").write_text(json.dumps(_valid()))
    assert triage.main(["validate", "--dir", str(tmp_path)]) == 0


def test_schema_enum_matches_taxonomy():
    schema = triage.load_schema()
    for k in ("behavior_classes", "behavior_classes_primary", "behavior_classes_secondary"):
        assert schema["properties"][k]["items"]["enum"] == behavior_class_ids()


def test_api_schema_strips_unsupported_keywords():
    s = json.dumps(triage.api_schema())
    for k in ("pattern", "minimum", "maximum", "minLength", "uniqueItems", "$schema"):
        assert f'"{k}"' not in s
    assert triage.api_schema()["properties"]["effective_date"] == {"anyOf": [{"type": "string"}, {"type": "null"}]}
    api = triage.api_schema()
    assert "behavior_classes" not in api["properties"] and "anyOf" not in api
    assert {"behavior_classes_primary", "behavior_classes_secondary"} <= set(api["required"])


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
    assert "| Specificity (end to end) | 2/2 |" in text and "## Relevance: triage alone" in text
    assert "| Prefilter recall |" in text and "Model errors (end to end): FIXTURE-0012 FN (from triage)" in text
    assert "FIXTURE-0011" in text  # reported as missing
    assert "Sample-size caveat" in text


def test_eval_without_labels_writes_status(tmp_path):
    import run_eval
    out = tmp_path / "results.md"
    assert run_eval.main(["--labels", str(ROOT / "eval" / "labels.csv"), "--data-dir", str(tmp_path), "--out", str(out)]) == 0
    assert "No results yet" in out.read_text()


def test_eval_reports_stage_b_changes(tmp_path):
    import run_eval
    triage, stage_a = tmp_path / "triage", tmp_path / "triage_stage_a"
    triage.mkdir()
    stage_a.mkdir()
    for d in ("A", "B", "C", "D"):
        (stage_a / f"{d}.json").write_text("{}")
    rows = [{"doc_id": "A", "direction": "not_relevant_to_relevant", "fields_changed": ["relevant"]},
            {"doc_id": "B", "direction": "relevant_to_not_relevant", "fields_changed": ["relevant"]},
            {"doc_id": "C", "direction": None, "fields_changed": ["behavior_classes"]}]
    (triage / "_stage_b.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    sb = run_eval.stage_b_summary(triage)
    assert sb == {"stage_a_total": 4, "stage_b_reads": 3, "to_relevant": 1, "to_not_relevant": 1, "other_fields_changed": 1}
    out = tmp_path / "results.md"
    assert run_eval.main(["--labels", str(ROOT / "eval" / "labels.csv"), "--triage-dir", str(triage),
                          "--data-dir", str(tmp_path), "--out", str(out)]) == 0
    assert "changed the Stage A relevance answer for 2 of 3" in out.read_text()


def test_clopper_pearson_known_values():
    import run_eval
    lo, hi = run_eval.clopper_pearson(15, 15)
    assert abs(lo - 0.025 ** (1 / 15)) < 1e-9 and hi == 1.0
    lo, hi = run_eval.clopper_pearson(7, 10)
    assert abs(lo - 0.3475) < 1e-3 and abs(hi - 0.9333) < 1e-3


def test_sample_selection(tmp_path):
    import select_sample
    w = json.loads((FIXTURES / "federal_register" / "window.json").read_text())
    argv = ["--offline", "--start", w["start"], "--end", w["end"], "--out-dir", str(tmp_path)]
    assert select_sample.main(argv) == 0
    with open(tmp_path / "labels.csv") as f:
        rows = list(csv.DictReader(f))
    assert rows and all(r["label_relevant"] == "" for r in rows)
    assert len({r["doc_id"] for r in rows}) == len(rows)
    cand = (tmp_path / "candidates.md").read_text()
    assert all(r["doc_id"] in cand for r in rows)
    for word in ("relevant", "negative", "positive", "stratum"):
        assert word not in cand.lower()
    assert select_sample.main(argv) == 1  # no overwrite


# ------------------------------------------------------------ govinfo text
def test_html_to_text_strips_tags_and_entities():
    from pipeline.sources import html_to_text
    markup = "<html><head><style>p{}</style><script>x()</script></head><body><pre>AGENCY: CFPB &amp; FTC.\n<b>12 CFR</b> 1006</pre></body></html>"
    assert html_to_text(markup) == "AGENCY: CFPB & FTC.\n12 CFR 1006\n"


class _Resp:
    def __init__(self, status, text="", location=None):
        self.status_code, self.text = status, text
        self.headers = {"Location": location} if location else {}
        self.is_redirect = location is not None
        self.next = types.SimpleNamespace(url=location)

    def raise_for_status(self):
        import requests
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


def _live_client(monkeypatch, responses, key="k-test"):
    from pipeline import sources
    if key:
        monkeypatch.setenv("GOVINFO_API_KEY", key)
    else:
        monkeypatch.delenv("GOVINFO_API_KEY", raising=False)
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    c = sources.LiveClient(retries=1)
    calls = []

    def get(url, params=None, headers=None, **kw):
        calls.append((url, dict(headers or {})))
        return responses(url)
    c.session = types.SimpleNamespace(get=get, headers={})
    return c, calls


DOC = {"document_number": "2025-08641", "publication_date": "2025-05-15"}


def test_govinfo_api_route_sends_key_in_header_only(monkeypatch):
    c, calls = _live_client(monkeypatch, lambda url: _Resp(200, "<pre>text</pre>"))
    assert c.get_document_html(DOC) == ("<pre>text</pre>", "api")
    url, headers = calls[0]
    assert url == "https://api.govinfo.gov/packages/FR-2025-05-15/granules/2025-08641/htm"
    assert headers == {"X-Api-Key": "k-test"} and "k-test" not in url


def test_govinfo_falls_back_to_www(monkeypatch):
    c, calls = _live_client(monkeypatch, lambda url: _Resp(403) if "api." in url else _Resp(200, "<pre>w</pre>"))
    assert c.get_document_html(DOC) == ("<pre>w</pre>", "www")
    assert calls[-1] == ("https://www.govinfo.gov/content/pkg/FR-2025-05-15/html/2025-08641.htm", {})
    c, calls = _live_client(monkeypatch, lambda url: _Resp(200, "w"), key=None)
    assert c.get_document_html(DOC) == ("w", "www") and len(calls) == 1


def test_govinfo_unavailable_reason_never_contains_key(monkeypatch):
    from pipeline.sources import TextUnavailable
    c, _ = _live_client(monkeypatch, lambda url: _Resp(429))
    with pytest.raises(TextUnavailable) as e:
        c.get_document_html(DOC)
    assert str(e.value) == "api: HTTP 429; www: HTTP 429" and "k-test" not in str(e.value)


def test_key_header_not_forwarded_off_host(monkeypatch):
    def responses(url):
        if url.startswith("https://api.govinfo.gov"):
            return _Resp(302, location="https://elsewhere.example/x")
        return _Resp(200, "moved")
    c, calls = _live_client(monkeypatch, responses)
    assert c.get_document_html(DOC) == ("moved", "api")
    assert calls[1] == ("https://elsewhere.example/x", {})


def test_fetch_texts_caches_and_never_refetches(tmp_path):
    from pipeline import ingest
    from pipeline.common import data_paths, write_json, write_jsonl

    class Counting:
        n = 0

        def get_document_html(self, doc):
            Counting.n += 1
            return "<pre>Body &amp; more</pre>", "api"
    p = data_paths(tmp_path)
    write_jsonl(p["prefilter"] / "kept.jsonl", [{"document_number": "2025-08641"}])
    write_json(p["raw"] / "2025-08641.json", {"document": DOC})
    res = ingest.fetch_texts(Counting(), tmp_path)
    assert res["fetched_now"] == 1 and Counting.n == 1
    from pipeline.common import read_gz_text
    assert read_gz_text(p["html"] / "2025-08641.htm.gz") == "<pre>Body &amp; more</pre>"
    assert (p["text"] / "2025-08641.txt").read_text() == "Body & more\n"
    (p["text"] / "2025-08641.txt").unlink()        # derived text lost, cached response kept
    assert ingest.fetch_texts(Counting(), tmp_path)["fetched_now"] == 0 and Counting.n == 1
    assert (p["text"] / "2025-08641.txt").exists()


def test_triage_rows_adds_dropped_eval_documents(tmp_path, monkeypatch):
    from pipeline import common
    from pipeline.common import data_paths, write_jsonl
    p = data_paths(tmp_path)
    write_jsonl(p["prefilter"] / "kept.jsonl", [{"document_number": "K1"}, {"document_number": "E1"}])
    write_jsonl(p["prefilter"] / "dropped.jsonl", [{"document_number": "E2"}, {"document_number": "D1"}])
    labels = tmp_path / "labels.csv"
    labels.write_text("doc_id,label_relevant\nE1,\nE2,\n")
    monkeypatch.setattr(common, "EVAL_LABELS_PATH", labels)
    assert [r["document_number"] for r in common.triage_rows(tmp_path)] == ["K1", "E1"]
    assert [r["document_number"] for r in common.triage_rows(tmp_path, include_eval=True)] == ["K1", "E1", "E2"]


def test_ingest_serves_closed_months_from_store(tmp_path):
    import datetime as dt
    from pipeline import ingest, sources
    from pipeline.common import data_paths, read_jsonl_gz

    class Counting(sources.FixtureClient):
        calls = 0

        def get_json(self, url, params=None):
            Counting.calls += 1
            return super().get_json(url, params)
    start, end, today = dt.date(2024, 9, 1), dt.date(2026, 8, 31), dt.date(2026, 9, 10)
    m1 = ingest.ingest(Counting(), start, end, tmp_path, today)
    first = Counting.calls
    assert first > 0 and m1["agency_months_from_store"] == 0
    assert len(read_jsonl_gz(data_paths(tmp_path)["fr_store"])) == m1["unique_documents"] == 16
    m2 = ingest.ingest(Counting(), start, end, tmp_path, today)
    assert Counting.calls == first and m2["agency_months_requested"] == 0
    assert m2["unique_documents"] == 16 and m2["complete"]
    # a month fetched before it ended is queried again
    m3 = ingest.ingest(Counting(), start, end, tmp_path / "b", dt.date(2026, 8, 15))
    m4 = ingest.ingest(Counting(), start, end, tmp_path / "b", dt.date(2026, 8, 15))
    assert m4["agency_months_requested"] == len(ingest.config.AGENCIES)


def test_ecfr_full_text_cached(tmp_path):
    from pipeline import config, sources

    class Inner:
        n = 0

        def get_text(self, url, params=None):
            Inner.n += 1
            return "<xml/>"
    c = sources.EcfrTextCache(Inner(), tmp_path)
    url = f"{config.ECFR_API}/full/2025-06-01/title-12.xml"
    assert c.get_text(url, {"part": "1006", "section": "1006.14"}) == "<xml/>"
    assert c.get_text(url, {"part": "1006", "section": "1006.14"}) == "<xml/>" and Inner.n == 1
    c.get_text(f"{config.ECFR_API}/versions/title-12.json", {"part": "1006"})
    c.get_text(f"{config.ECFR_API}/versions/title-12.json", {"part": "1006"})
    assert Inner.n == 3  # versions index is never served from disk


# ------------------------------------------------------------------ secrets
SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"ANTHROPIC_API_KEY\s*[=:]\s*['\"]?[A-Za-z0-9_-]{20,}"),
    re.compile(r"GOVINFO_API_KEY\s*[=:]\s*['\"]?[A-Za-z0-9_-]{20,}"),
    re.compile(r"api_key=[A-Za-z0-9]{20,}"),
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


# ------------------------------------------------------------ record metadata
_RECORD = "# Change record: {d}\n\n| Change type | proposed_rule |\n\nBehavior classes: `PAYMENT.FEES`\n\n## What a compliant agent must now do\n\nX.\n\n## Triage\n\n- Relevant: True\n\n## Reviewer sign-off\n\n- Decision: [ ] Confirm relevant, implement  [ ] Not relevant, close  [ ] Escalate to counsel\n- Reviewer:\n- Date:\n- Notes:\n"


def _meta_dir(tmp_path, meta):
    import yaml
    from pipeline.common import write_jsonl_gz
    for d in ("P-1", "W-2"):
        (tmp_path / f"{d}.md").write_text(_RECORD.format(d=d))
    (tmp_path / "record_meta.yaml").write_text(yaml.safe_dump({"records": meta}))
    store = tmp_path / "store.jsonl.gz"
    write_jsonl_gz(store, [{"document": {"document_number": d}} for d in ("P-1", "W-2")])
    return store


def test_record_supersession_links(tmp_path):
    from pipeline import records
    meta = {"P-1": {"superseded_by": [{"doc_id": "W-2", "relation": "withdrawal"}]},
            "W-2": {"supersedes": [{"doc_id": "P-1", "relation": "withdrawal"}]}}
    store = _meta_dir(tmp_path, meta)
    assert records.check_meta(tmp_path, store) == []
    assert records.annotate(tmp_path)["annotated"] == ["P-1", "W-2"]
    text = (tmp_path / "P-1.md").read_text()
    assert "- Record status: closed by W-2 (withdrawal)" in text and "[W-2](W-2.md): withdrawal (closes this record" in text
    assert text.index("## Supersession") < text.index("## Triage")
    assert "- Record status: open" in (tmp_path / "W-2.md").read_text()
    assert records.annotate(tmp_path)["annotated"] == []  # idempotent
    meta["W-2"] = {}  # link not mirrored; unknown relation; document outside the store
    meta["P-1"]["superseded_by"] += [{"doc_id": "X-9", "relation": "repeal"}]
    _meta_dir(tmp_path, meta)
    errs = records.check_meta(tmp_path, store)
    assert any("not mirrored" in e for e in errs) and any("unknown relation" in e for e in errs)
    assert any("not in the ingested store" in e for e in errs)


def test_record_change_type_interpretation(tmp_path):
    from pipeline import records
    _meta_dir(tmp_path, {"P-1": {"change_type": "interpretation", "change_type_reason": "Supervisory findings"}})
    records.annotate(tmp_path)
    text = (tmp_path / "P-1.md").read_text()
    assert "| Change type | interpretation |" in text and "| Required action | Control validation" in text
    assert "| Change type basis | Supervisory findings |" in text
    assert text.count(records.INTERPRETATION_NOTE) == 1
    assert records.annotate(tmp_path)["annotated"] == []  # idempotent


def test_record_primary_secondary_retag(tmp_path):
    from pipeline import records
    meta = {"P-1": {"behavior_classes_primary": [], "behavior_classes_secondary": ["PAYMENT.FEES"],
                    "tagging_note": "No primary class: proposal withdrawn."}}
    store = _meta_dir(tmp_path, meta)
    for _ in range(2):  # the second run must not duplicate the rendered class lines
        records.annotate(tmp_path)
    text = (tmp_path / "P-1.md").read_text()
    assert text.count("Primary behavior classes (drive routing and review): none") == 1
    assert text.count("Secondary behavior classes (context only): `PAYMENT.FEES`") == 1
    assert text.count("Tagging note:") == 1 and "Behavior classes:" not in text
    meta["P-1"]["behavior_classes_primary"] = ["PAYMENT.FEES"]
    _meta_dir(tmp_path, meta)
    assert any("both primary and secondary" in e for e in records.check_meta(tmp_path, store))


def test_review_overrides(tmp_path):
    """A not_relevant review signs and closes the record; a relevant review of a
    not-relevant model answer creates the record from committed data."""
    import yaml
    from pipeline import records
    real = records.load_record_meta()
    meta = {"P-1": {"review": {"decision": "not_relevant", "reviewer": "R", "date": "2026-01-01", "reason": "Out of scope."}},
            "2025-22490": real["2025-22490"]}
    _meta_dir(tmp_path, meta)
    (tmp_path / "record_meta.yaml").write_text(yaml.safe_dump({"records": meta}))
    (tmp_path / "REVIEW_QUEUE.md").write_text("| [P-1](u) | T | Rule | 2026 | relevant | True | 0.70 | [record](P-1.md) |\n")
    res = records.annotate(tmp_path)
    assert res["created_by_review"] == ["2025-22490"]
    closed = (tmp_path / "P-1.md").read_text()
    assert "[x] Not relevant, close" in closed and "- Reviewer: R" in closed and records.SIGNED_OFF.search(closed)
    assert "human review: not relevant, closed |" in (tmp_path / "REVIEW_QUEUE.md").read_text()
    created = (tmp_path / "2025-22490.md").read_text()
    assert "- Relevant: False" in created  # the model's answer is shown, not rewritten
    assert "| Change type | interpretation (v1 triage output: proposed_rule) |" in created
    assert "Primary behavior classes (drive routing and review): `DATA.PRIVACY_SECURITY`" in created
    assert not records.SIGNED_OFF.search(created)  # confirmed relevant; still awaits sign-off
    assert records.annotate(tmp_path)["annotated"] == []
