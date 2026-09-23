import json

from pipeline import ingest, sources
from pipeline.common import data_paths, read_json, read_jsonl
from pipeline.config import AGENCIES


def test_end_to_end_offline(offline_run):
    assert offline_run["rc"] == 0
    p = data_paths(offline_run["data"])
    m = read_json(p["manifest"])
    assert m["offline_fixture"] and m["complete"]
    assert set(m["per_agency"]) == set(AGENCIES)
    # 17 fixtures; FIXTURE-0016 is outside the window; FIXTURE-0015 has 3 agencies but is stored once
    assert m["unique_documents"] == 16
    assert not (p["raw"] / "FIXTURE-0016.json").exists()
    assert sorted(read_json(p["raw"] / "FIXTURE-0015.json")["matched_agency_queries"]) == sorted([
        "comptroller-of-the-currency", "federal-deposit-insurance-corporation", "federal-reserve-system"])
    # raw JSON keeps the abstract
    assert read_json(p["raw"] / "FIXTURE-0001.json")["document"]["abstract"]


def test_prefilter_decisions_are_all_logged(offline_run):
    p = data_paths(offline_run["data"])
    kept = {r["document_number"]: r["reason"] for r in read_jsonl(p["prefilter"] / "kept.jsonl")}
    dropped = {r["document_number"]: r["reason"] for r in read_jsonl(p["prefilter"] / "dropped.jsonl")}
    assert len(kept) + len(dropped) == 16 and not set(kept) & set(dropped)
    assert kept["FIXTURE-0001"] == "tracked_cfr_part"
    assert kept["FIXTURE-0002"] == "domain_terms"          # guidance withdrawal
    assert kept["FIXTURE-0010"] == "withdrawal_or_rescission"
    assert kept["FIXTURE-0017"] == "cfpb_rulemaking"
    assert kept["FIXTURE-0006"] == "domain_terms"          # hard negative reaches triage
    assert dropped == {"FIXTURE-0004": "noise_title", "FIXTURE-0005": "noise_title",
                       "FIXTURE-0009": "noise_title", "FIXTURE-0013": "noise_title",
                       "FIXTURE-0014": "no_signal"}


def test_diff_statuses(offline_run):
    p = data_paths(offline_run["data"])
    d1 = read_json(p["diffs"] / "FIXTURE-0001.json")
    assert d1["status"] == "diffed"
    by_sec = {s["section"]: s for s in d1["sections"]}
    assert by_sec["1006.14"]["change"] == "amended"
    assert "+(b)(2) Telephone call frequencies. A debt collector is presumed to comply if it places a telephone call or sends a text message" in by_sec["1006.14"]["unified_diff"]
    assert by_sec["1006.15"]["change"] == "added"
    assert read_json(p["diffs"] / "FIXTURE-0003.json")["status"] == "pending_effective"
    assert read_json(p["diffs"] / "FIXTURE-0007.json")["status"] == "proposed_no_ecfr_change"
    assert read_json(p["diffs"] / "FIXTURE-0008.json")["status"] == "no_matching_ecfr_version"
    assert not (p["diffs"] / "FIXTURE-0011.json").exists()  # 12 CFR 748 is kept but not diffed


def test_route_and_records(offline_run):
    p = data_paths(offline_run["data"])
    closed = {i["doc_id"] for i in read_json(p["queue"] / "auto_closed.json")}
    review = {i["doc_id"]: i["route_reason"] for i in read_json(p["queue"] / "review_queue.json")}
    assert closed == {"FIXTURE-0006"}
    # 0010 and 0012 have triage outputs but no full text: not triaged from partial information.
    assert review["FIXTURE-0010"] == "full_text_unavailable"
    assert review["FIXTURE-0012"] == "full_text_unavailable"
    assert review["FIXTURE-0011"] == "full_text_unavailable"
    rec = offline_run["records"]
    assert {f.stem for f in rec.glob("FIXTURE-*.md")} == {"FIXTURE-0001", "FIXTURE-0002", "FIXTURE-0003", "FIXTURE-0007"}
    text = (rec / "FIXTURE-0001.md").read_text()
    for heading in ("## Document", "## What changed", "## Affected register rows and behavior classes",
                    "## What a compliant agent must now do", "## Questions the deploying team must answer",
                    "## Triage", "## Reviewer sign-off", "```diff", "Owning config/script", "Approver",
                    "Rollout sequence", "Test evidence required"):
        assert heading in text
    assert "FIXTURE-0011" in (rec / "REVIEW_QUEUE.md").read_text()


def test_signed_record_not_overwritten(offline_run):
    from pipeline import records
    rec = offline_run["records"] / "FIXTURE-0001.md"
    signed = rec.read_text().replace("- Reviewer:", "- Reviewer: A. Reviewer")
    rec.write_text(signed)
    res = records.run(offline_run["data"], offline_run["records"])
    assert res["signed_records_preserved"] == ["FIXTURE-0001"]
    assert rec.read_text() == signed


def test_ingest_pagination_and_splitting(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "PER_PAGE", 1)
    monkeypatch.setattr(ingest, "MAX_RETRIEVABLE", 1)
    import datetime as dt
    m = ingest.ingest(sources.FixtureClient(), dt.date(2024, 9, 1), dt.date(2026, 8, 31), tmp_path)
    assert m["complete"] and m["unique_documents"] == 16


def test_triage_packets(offline_run):
    p = data_paths(offline_run["data"])
    pk = read_json(p["triage_inputs"] / "FIXTURE-0001.json")
    assert pk["doc_id"] == "FIXTURE-0001"
    assert pk["full_text_excerpt"].startswith("[SYNTHETIC FIXTURE FULL TEXT]")
    assert pk["ecfr_diff"]["status"] == "diffed"
    assert json.dumps(pk)  # serializable
