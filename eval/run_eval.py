"""Score triage against blind labels (BUILD_SPEC Section 10) and write results.md.

    python eval/run_eval.py [--labels eval/labels.csv] [--triage-dir data/triage]
                            [--data-dir DIR] [--out eval/results.md]

End-to-end prediction per labeled document:
  - dropped by the prefilter        -> predicted not relevant (source: prefilter)
  - triage output present           -> triage `relevant` (source: triage)
  - kept but no triage output       -> excluded from scoring, reported as missing
Triage-only prediction: triage `relevant` for every labeled document with a triage
output, whatever its prefilter decision (eval documents are triaged with --include-eval).
Prefilter decisions come from data/prefilter/{kept,dropped}.jsonl when present, else
from pipeline.prefilter.classify over the committed metadata store.
Labels: label_relevant Y/N; label_behavior_classes separated by ';'; label_tier 1/2.
Rows with a blank label_relevant are unlabeled and excluded.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import prefilter  # noqa: E402
from pipeline.triage import class_tags  # noqa: E402
from pipeline.common import data_paths, load_register, read_jsonl, read_jsonl_gz  # noqa: E402


def _binom_cdf(k: int, n: int, p: float) -> float:
    if p <= 0:
        return 1.0
    if p >= 1:
        return 0.0 if k < n else 1.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def clopper_pearson(x: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact two-sided (1-alpha) binomial interval."""
    if n == 0:
        return (0.0, 1.0)
    lower = 0.0 if x == 0 else _solve_lower(x, n, alpha)
    upper = 1.0 if x == n else _solve_upper(x, n, alpha)
    return lower, upper


def _bisect(fn, target, increasing):
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        v = fn(mid)
        if (v < target) == increasing:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _solve_lower(x, n, alpha):
    # P(X >= x | p) = alpha/2 ; increasing in p
    return _bisect(lambda p: 1 - _binom_cdf(x - 1, n, p), alpha / 2, increasing=True)


def _solve_upper(x, n, alpha):
    # P(X <= x | p) = alpha/2 ; decreasing in p
    return _bisect(lambda p: _binom_cdf(x, n, p), alpha / 2, increasing=False)


def _yn(v):
    v = (v or "").strip().upper()
    return True if v in ("Y", "YES", "TRUE", "1") else False if v in ("N", "NO", "FALSE", "0") else None


def _classes(v):
    return {c.strip() for c in (v or "").replace(",", ";").split(";") if c.strip()}


def prefilter_decisions(paths: dict) -> tuple[set[str], set[str]]:
    """(kept, dropped) document numbers: the prefilter logs if they hold any records,
    else the prefilter's own classify() applied to the committed metadata store."""
    logged = [{r["document_number"] for r in read_jsonl(paths["prefilter"] / f"{k}.jsonl")}
              for k in ("kept", "dropped") if (paths["prefilter"] / f"{k}.jsonl").exists()]
    if len(logged) == 2 and (logged[0] or logged[1]):
        return logged[0], logged[1]
    kept, dropped = set(), set()
    if paths["fr_store"].exists():
        for rec in read_jsonl_gz(paths["fr_store"]):
            doc = rec["document"]
            (kept if prefilter.classify(doc)["keep"] else dropped).add(doc["document_number"])
    return kept, dropped


def evaluate(labels_path: Path, triage_dir: Path, dropped: set[str], kept: set[str] | None = None) -> dict:
    with open(labels_path) as f:
        rows = list(csv.DictReader(f))
    tiers = {r["id"]: r["tier"] for r in load_register()}
    res = {"sample_rows": len(rows), "labeled": 0, "unlabeled": 0, "missing_prediction": [],
           "tp": 0, "fp": 0, "fn": 0, "tn": 0, "by_source": {"prefilter": 0, "triage": 0},
           "class_pairs": [], "tier_pairs": [], "errors": [], "tiers_labeled": 0,
           "triage_only": {"tp": 0, "fp": 0, "fn": 0, "tn": 0}, "pf_pos_kept": 0, "pf_pos_dropped": 0}
    for r in rows:
        label = _yn(r.get("label_relevant"))
        if label is None:
            res["unlabeled"] += 1
            continue
        res["labeled"] += 1
        doc_id = r["doc_id"]
        tpath = triage_dir / f"{doc_id}.json"
        if r.get("label_tier", "").strip():
            res["tiers_labeled"] += 1
        if label and doc_id in dropped:
            res["pf_pos_dropped"] += 1
        elif label and (kept is None or doc_id in kept):
            res["pf_pos_kept"] += 1
        if tpath.exists():
            t_pred = bool(json.loads(tpath.read_text()).get("relevant"))
            res["triage_only"][("tp" if t_pred else "fn") if label else ("fp" if t_pred else "tn")] += 1
        if doc_id in dropped:
            pred, out, src = False, None, "prefilter"
        elif tpath.exists():
            out = json.loads(tpath.read_text())
            pred, src = bool(out.get("relevant")), "triage"
        else:
            res["missing_prediction"].append(doc_id)
            continue
        res["by_source"][src] += 1
        key = ("tp" if pred else "fn") if label else ("fp" if pred else "tn")
        res[key] += 1
        if key in ("fp", "fn"):
            res["errors"].append((doc_id, key.upper(), src))
        if label and pred and out is not None:
            res["class_pairs"].append((doc_id, _classes(r.get("label_behavior_classes")), set().union(*class_tags(out))))
            pred_tiers = [tiers[i] for i in out.get("affected_register_rows", []) if i in tiers]
            if r.get("label_tier", "").strip() and pred_tiers:
                res["tier_pairs"].append((doc_id, int(r["label_tier"]), min(pred_tiers)))
    return res


def stage_b_summary(triage_dir: Path) -> dict | None:
    """Counts from <triage_dir>/_stage_b.jsonl: how many Stage B full-text reads
    changed the Stage A relevance call, and in which direction."""
    path = Path(triage_dir) / "_stage_b.jsonl"
    if not path.exists():
        return None
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    stage_a = [json.loads(f.read_text()) for f in (Path(triage_dir).parent / "triage_stage_a").glob("*.json")]
    return {
        "stage_a_total": len(stage_a),
        "stage_b_reads": len(rows),
        "to_relevant": sum(1 for r in rows if r.get("direction") == "not_relevant_to_relevant"),
        "to_not_relevant": sum(1 for r in rows if r.get("direction") == "relevant_to_not_relevant"),
        "other_fields_changed": sum(1 for r in rows if not r.get("direction") and r.get("fields_changed")),
    }


def _render_stages(sb: dict | None) -> list[str]:
    if not sb:
        return []
    changed = sb["to_relevant"] + sb["to_not_relevant"]
    return ["## Triage method: Stage A screening and Stage B full-text reads", "",
            f"- Stage A (abstract, metadata and eCFR diff excerpt only): {sb['stage_a_total']} documents.",
            f"- Stage B (saved full text, about 4,000 words at most) for every Stage A 'relevant' call and every "
            f"call with confidence below 0.7: {sb['stage_b_reads']} documents.",
            f"- Stage B changed the Stage A relevance answer for {changed} of {sb['stage_b_reads']}: "
            f"{sb['to_relevant']} not relevant to relevant, {sb['to_not_relevant']} relevant to not relevant.",
            f"- Stage B kept the relevance answer but changed register rows, behavior classes, change type or "
            f"effective date for {sb['other_fields_changed']} more.",
            "- Predictions scored here are the post-Stage-B answers in the triage directory; Stage A answers are "
            "kept in `data/triage_stage_a/`.", ""]


def _pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _rate(name: str, x: int, n: int, of: str) -> str:
    """Markdown table row: raw fraction, point estimate, exact 95% interval, what n counts."""
    if not n:
        return f"| {name} | 0/0 | n/a | n/a | {of} |"
    lo, hi = clopper_pearson(x, n)
    return f"| {name} | {x}/{n} | {_pct(x / n)} | {_pct(lo)} to {_pct(hi)} | {of} |"


def _matrix(c: dict) -> list[str]:
    return ["| | Labeled relevant | Labeled not relevant |", "|---|---|---|",
            f"| Predicted relevant | TP {c['tp']} | FP {c['fp']} |",
            f"| Predicted not relevant | FN {c['fn']} | TN {c['tn']} |", ""]


def render(res: dict, labels_path: Path, triage_dir: Path, stages: dict | None = None) -> str:
    out = ["# Eval results", "",
           "<!-- GENERATED by eval/run_eval.py. Do not edit by hand. -->", "",
           f"- Labels: `{labels_path.relative_to(ROOT) if labels_path.is_relative_to(ROOT) else labels_path}`",
           f"- Triage outputs: `{triage_dir.relative_to(ROOT) if triage_dir.is_relative_to(ROOT) else triage_dir}`",
           f"- Sample rows: {res['sample_rows']}; labeled: {res['labeled']}; unlabeled: {res['unlabeled']}; "
           f"labeled but no prediction yet: {len(res['missing_prediction'])}", ""]
    scored = res["tp"] + res["fp"] + res["fn"] + res["tn"]
    if scored == 0:
        out += ["## Status", "",
                "**No results yet.** Nothing can be scored until labeled documents also have predictions.",
                "",
                "Protocol (BUILD_SPEC Section 10):",
                "1. Run `python eval/select_sample.py` to draw 30 documents from direct Federal Register term searches "
                "(query mix in the script docstring; at least 5 prefilter-dropped documents).",
                "2. The labeler fills in `eval/labels.csv` **blind**, before seeing any triage output "
                "or `eval/sample_manifest.csv`: relevant Y/N, behavior classes, tier.",
                "3. Run triage, then `python eval/run_eval.py`.", ""]
        if res["missing_prediction"]:
            out += ["Labeled documents awaiting triage: " + ", ".join(res["missing_prediction"]), ""]
        return "\n".join(out + _render_stages(stages))
    pos, pred_pos, neg = res["tp"] + res["fn"], res["tp"] + res["fp"], res["fp"] + res["tn"]
    t = res["triage_only"]
    t_pos, t_neg = t["tp"] + t["fn"], t["fp"] + t["tn"]
    pf_n = res["pf_pos_kept"] + res["pf_pos_dropped"]
    out += ["## Relevance: end to end (prefilter, then triage)", "",
            "A prefilter drop counts as a 'not relevant' prediction.", ""] + _matrix(res) + [
            f"Predictions from triage: {res['by_source']['triage']}; from prefilter drops: {res['by_source']['prefilter']}.", "",
            "## Relevance: triage alone", "",
            f"Every labeled document with a triage output ({t_pos + t_neg}), including prefilter-dropped eval documents.", ""
            ] + _matrix(t) + [
            "## Rates", "",
            "Exact (Clopper-Pearson) two-sided 95% intervals. n is the denominator.", "",
            "| Metric | Raw fraction | Point estimate | 95% interval | Denominator |", "|---|---|---|---|---|",
            _rate("Precision (end to end)", res["tp"], pred_pos, "documents the pipeline marked relevant"),
            _rate("Recall (triage alone)", t["tp"], t_pos, "labeled-relevant documents with a triage output"),
            _rate("Specificity (triage alone)", t["tn"], t_neg, "labeled-not-relevant documents with a triage output"),
            _rate("Prefilter recall", res["pf_pos_kept"], pf_n, "labeled-relevant documents; numerator = kept by the prefilter"),
            _rate("End-to-end recall", res["tp"], pos, "labeled-relevant documents; numerator = kept and triaged relevant"),
            _rate("Specificity (end to end)", res["tn"], neg, "labeled-not-relevant documents"),
            _rate("Precision (triage alone)", t["tp"], t["tp"] + t["fp"], "documents triage marked relevant"), ""]
    if res["errors"]:
        out += ["Model errors (end to end): " + "; ".join(f"{d} {k} (from {s})" for d, k, s in res["errors"]) + ".", ""]
        if (ROOT / "eval" / "error_analysis.md").exists():
            out += ["Root-cause analysis of each error: `eval/error_analysis.md` (hand-written after scoring).", ""]
    if res["class_pairs"]:
        jac = [len(a & b) / len(a | b) if a | b else 1.0 for _, a, b in res["class_pairs"]]
        exact = sum(1 for _, a, b in res["class_pairs"] if a == b)
        out += ["## Behavior-class agreement (true positives only)", "",
                f"- Documents compared: {len(jac)}",
                f"- Mean Jaccard overlap: {sum(jac) / len(jac):.2f}",
                f"- Exact set match: {exact}/{len(jac)}",
                f"- Class instances: {sum(len(a & b) for _, a, b in res['class_pairs'])} of "
                f"{sum(len(a) for _, a, b in res['class_pairs'])} labeled classes predicted; "
                f"{sum(len(a & b) for _, a, b in res['class_pairs'])} of {sum(len(b) for _, a, b in res['class_pairs'])} "
                "predicted classes labeled (instances within a document are not independent, so no interval is given).", "",
                "| Document | Labeled classes | Predicted classes |", "|---|---|---|"]
        out += [f"| {d} | {', '.join(sorted(a)) or '—'} | {', '.join(sorted(b)) or '—'} |" for d, a, b in res["class_pairs"]]
        out.append("")
    if not res["tiers_labeled"]:
        out += ["## Tier agreement", "", "Not scored: no labeled document has a tier.", ""]
    if res["tier_pairs"]:
        agree = sum(1 for _, a, b in res["tier_pairs"] if a == b)
        out += ["## Tier agreement", "",
                f"Predicted tier = lowest tier among the affected register rows. Agreement: {agree}/{len(res['tier_pairs'])}.", ""]
    out += ["## Sample-size caveat", "",
            f"This eval has {pos} labeled positives and {scored - pos} labeled negatives. At this size the "
            "intervals above are wide, and they are the honest summary. For example, perfect recall on "
            f"{pos} positives would give a 95% two-sided lower bound of {_pct(clopper_pearson(pos, pos)[0])}; "
            f"one miss moves recall by {_pct(1 / pos) if pos else 'n/a'}.", ""]
    if res["missing_prediction"]:
        out += ["Labeled documents without a prediction (excluded): " + ", ".join(res["missing_prediction"]), ""]
    return "\n".join(out + _render_stages(stages))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", default=str(ROOT / "eval" / "labels.csv"))
    ap.add_argument("--data-dir")
    ap.add_argument("--triage-dir")
    ap.add_argument("--out", default=str(ROOT / "eval" / "results.md"))
    args = ap.parse_args(argv)
    paths = data_paths(args.data_dir)
    triage_dir = Path(args.triage_dir) if args.triage_dir else paths["triage"]
    kept, dropped = prefilter_decisions(paths)
    labels = Path(args.labels).resolve()
    res = evaluate(labels, triage_dir.resolve(), dropped, kept)
    Path(args.out).write_text(render(res, labels, triage_dir.resolve(), stage_b_summary(triage_dir)) + "\n")
    print(f"eval: labeled {res['labeled']}, TP {res['tp']} FP {res['fp']} FN {res['fn']} TN {res['tn']} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
