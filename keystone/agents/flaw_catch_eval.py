"""
keystone.agents.flaw_catch_eval
==============================
Measure whether Keystone's agents CATCH a planted flaw. For each flaw in the
deterministic catalogue we inject it (``keystone.deterministic.flaw_injection``),
re-run the Evidence-Quality + Reviewer agents on the flawed graph, and ask: did
the assessment change (caught) or stay identical (missed — confident-wrong)?

Benign perturbations are the negative class, so precision/recall are real. Output
matches ``calibrate.py``: accuracy vs. coin flip, confusion matrix, disagreements.

    python -m keystone.agents.flaw_catch_eval               # heuristic, offline
    KEYSTONE_LIVE=1 ... python -m keystone.agents.flaw_catch_eval   # Claude agents

Only this catching step may call an LLM; injection never does.
"""
from __future__ import annotations

import argparse
import os
import sys

from keystone.deterministic.flaw_injection import (
    FLAW_CATALOGUE, BENIGN_CATALOGUE, inject_flaw, apply_benign)
from keystone.workbench import run


def _reasoner():
    if os.environ.get("KEYSTONE_LIVE") == "1":
        from keystone.agents.claude_reasoner import ClaudeReasoner
        return ClaudeReasoner()
    from keystone.agents.reasoner import HeuristicReasoner
    return HeuristicReasoner()


def _graph_builder(domain: str):
    if domain == "insulin":
        from keystone.data_insulin import build_insulin_graph
        return build_insulin_graph
    from keystone.data_gbm import build_gbm_graph
    return build_gbm_graph


def _assessment(graph, reasoner) -> dict:
    """The agents' observable output on a graph: the Evidence-Quality
    load-bearing scores and the Reviewer's verdict/objections. run() mutates its
    container, so we hand it a copy and keep the caller's graph pristine."""
    g = graph.copy()
    _, _, review = run("flaw-eval", g, reasoner)
    return {
        "verdict": review.verdict.value,
        "adj_conf": round(review.adjusted_confidence.point, 2),
        "num_objections": len(review.objections),
        "load_bearing": {f"{e.src}->{e.dst}": round(e.load_bearing.point, 3)
                         for e in g.edges
                         if e.edge_type.value in ("cites", "depends_on")},
    }


def evaluate(reasoner, build_graph) -> dict:
    clean = _assessment(build_graph(), reasoner)
    samples = []

    for ft in FLAW_CATALOGUE:
        res = inject_flaw(build_graph(), ft)
        if res.planted is None:
            continue
        detected = _assessment(res.graph, reasoner) != clean
        samples.append({"flawed": True, "detected": detected,
                        "name": ft.value, "planted": res.planted})

    for bp in BENIGN_CATALOGUE:
        detected = _assessment(apply_benign(build_graph(), bp), reasoner) != clean
        samples.append({"flawed": False, "detected": detected,
                        "name": bp.value, "planted": None})

    tp = sum(1 for s in samples if s["flawed"] and s["detected"])
    fn = sum(1 for s in samples if s["flawed"] and not s["detected"])
    tn = sum(1 for s in samples if not s["flawed"] and not s["detected"])
    fp = sum(1 for s in samples if not s["flawed"] and s["detected"])
    n = len(samples)
    acc = (tp + tn) / n if n else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    disagreements = []
    for s in samples:
        if s["flawed"] and not s["detected"]:
            disagreements.append(("MISSED (confident-wrong)",
                                  s["planted"].description))
        elif not s["flawed"] and s["detected"]:
            disagreements.append(("FALSE ALARM", s["name"]))
    return {"n": n, "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
            "tp": tp, "tn": tn, "fp": fp, "fn": fn, "samples": samples,
            "disagreements": disagreements}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", choices=["gbm", "insulin"], default="gbm")
    args = ap.parse_args()
    reasoner = _reasoner()
    res = evaluate(reasoner, _graph_builder(args.domain))

    print("=" * 66)
    print(f"KEYSTONE flaw-catch eval — {getattr(reasoner, 'version', '?')} "
          f"[{args.domain}]")
    print("=" * 66)
    print(f"variants tested: {res['n']} "
          f"({res['tp'] + res['fn']} planted flaws + {res['tn'] + res['fp']} benign)")
    print(f"\nACCURACY = {res['accuracy']:.3f}   (coin flip 0.500)")
    print(f"precision={res['precision']:.3f}  recall={res['recall']:.3f}  "
          f"f1={res['f1']:.3f}")
    print("\nconfusion matrix")
    print("                 flagged        not flagged")
    print(f"  planted flaw    {res['tp']:>4} caught      {res['fn']:>4} MISSED")
    print(f"  benign change   {res['fp']:>4} false-alarm {res['tn']:>4} ok")
    print("\nper-flaw:")
    for s in res["samples"]:
        if s["flawed"]:
            mark = "caught" if s["detected"] else "MISSED"
            print(f"  [{mark:6}] {s['name']}")
    if res["disagreements"]:
        print("\nconfident-wrong / false alarms:")
        for kind, msg in res["disagreements"]:
            print(f"  [{kind}] {msg}")
    verdict = ("beats a coin flip" if res["accuracy"] > 0.5
               else "does NOT beat a coin flip")
    print(f"\nverdict: {verdict}. Missed flaws are the actionable finding — "
          f"they mark where the Reviewer is blind.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
