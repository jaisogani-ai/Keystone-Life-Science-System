"""
calibrate.py — turn the moat into a measured number, not a claim.

Measures ``classify_load_bearing`` agreement against a hand-labeled set of REAL
glioblastoma citing sentences (``keystone/calibration/gbm_citing_sentences.jsonl``,
labeled by semantic judgment: does the sentence rely on the cited paper's
specific experimental result?). Reports accuracy, a confusion matrix, and
precision/recall.

    python calibrate.py                     # GBM (default), offline
    python calibrate.py --domain insulin    # second domain — same classifier
    KEYSTONE_LIVE=1 ANTHROPIC_API_KEY=... python calibrate.py   # ClaudeReasoner

Target: beat 0.50 (a coin flip) and land near the 0.69-0.75 human-agreement band
that the load-bearing task itself carries. The payoff of two domains: if the
insulin number lands near the GBM number, "domain-agnostic" is measured fact.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_CAL = Path(__file__).parent / "keystone" / "calibration"
LABELS = {"gbm": _CAL / "gbm_citing_sentences.jsonl",
          "insulin": _CAL / "insulin_citing_sentences.jsonl"}
HUMAN_BAND = (0.69, 0.75)


def load_labeled(domain: str = "gbm") -> list[dict]:
    rows = []
    with open(LABELS[domain]) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def get_reasoner():
    if os.environ.get("KEYSTONE_LIVE") == "1":
        from keystone.agents.claude_reasoner import ClaudeReasoner
        return ClaudeReasoner()
    from keystone.agents.reasoner import HeuristicReasoner
    return HeuristicReasoner()


def evaluate(reasoner, rows: list[dict]) -> dict:
    tp = tn = fp = fn = 0
    disagreements = []
    for r in rows:
        truth = r["label"] == "load_bearing"
        pred = reasoner.is_load_bearing(r["sentence"])
        if pred and truth:
            tp += 1
        elif not pred and not truth:
            tn += 1
        elif pred and not truth:
            fp += 1
            disagreements.append(("false_positive", r["sentence"]))
        else:
            fn += 1
            disagreements.append(("false_negative", r["sentence"]))
    n = len(rows)
    acc = (tp + tn) / n if n else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"n": n, "accuracy": acc, "precision": prec, "recall": rec,
            "f1": f1, "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "disagreements": disagreements}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", choices=list(LABELS), default="gbm")
    args = ap.parse_args()
    reasoner = get_reasoner()
    rows = load_labeled(args.domain)
    res = evaluate(reasoner, rows)

    print("=" * 66)
    print(f"KEYSTONE load-bearing calibration — "
          f"{getattr(reasoner, 'version', '?')} [{args.domain}]")
    print("=" * 66)
    print(f"labeled real {args.domain} citing sentences: {res['n']}")
    print(f"\nACCURACY = {res['accuracy']:.3f}   "
          f"(coin flip 0.500 | human-agreement band "
          f"{HUMAN_BAND[0]:.2f}-{HUMAN_BAND[1]:.2f})")
    print(f"precision={res['precision']:.3f}  recall={res['recall']:.3f}  "
          f"f1={res['f1']:.3f}")
    print("\nconfusion matrix")
    print("                 pred load-bearing   pred incidental")
    print(f"  truth load-bearing   {res['tp']:>6}            {res['fn']:>6}")
    print(f"  truth incidental     {res['fp']:>6}            {res['tn']:>6}")

    verdict = ("BEATS the coin flip and lands in the human band"
               if res["accuracy"] >= HUMAN_BAND[0] else
               "BEATS the coin flip (below human band — tune cues / go live)"
               if res["accuracy"] > 0.5 else
               "DOES NOT beat a coin flip — the moat is not yet proven")
    print(f"\nverdict: {verdict}")
    if res["disagreements"]:
        print(f"\n{len(res['disagreements'])} disagreements (first 5):")
        for kind, s in res["disagreements"][:5]:
            print(f"  [{kind}] {s[:96]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
